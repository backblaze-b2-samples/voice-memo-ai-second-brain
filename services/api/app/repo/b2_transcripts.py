"""B2 helpers for the `transcripts/` prefix.

Each transcript is a JSON document at `transcripts/<YYYY>/<MM>/<stem>.json`
that mirrors the source memo's date-partitioned key shape. Failures during
transcription land at `transcripts/.failed/<stem>.json` so the UI can
display a `failed` status without polluting the success listing.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

TRANSCRIPTS_PREFIX = "transcripts/"
TRANSCRIPTS_FAILED_PREFIX = "transcripts/.failed/"


def _stem_for_memo_key(memo_key: str) -> str:
    """Derive the partition + stem we use for a memo's sibling artifacts.

    Input:  `audio/2026/05/note--<uuid>.wav`
    Output: `2026/05/note--<uuid>`
    """
    if not memo_key.startswith("audio/"):
        raise ValueError(f"Memo key must start with `audio/`: {memo_key!r}")
    rest = memo_key[len("audio/") :]
    body = rest.rsplit(".", 1)[0] if "." in rest else rest
    return body


def transcript_key_for(memo_key: str) -> str:
    """Compute the canonical transcript key for a memo."""
    return f"{TRANSCRIPTS_PREFIX}{_stem_for_memo_key(memo_key)}.json"


def failed_transcript_key_for(memo_key: str) -> str:
    """Compute the `.failed/` marker key for a memo."""
    return f"{TRANSCRIPTS_FAILED_PREFIX}{_stem_for_memo_key(memo_key)}.json"


def put_transcript(memo_key: str, payload: dict) -> str:
    """Write a transcript JSON; return the resulting key."""
    key = transcript_key_for(memo_key)
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 transcript write failed for {key!r}: {e}") from e
    return key


def put_failed_marker(memo_key: str, payload: dict) -> str:
    """Write a `.failed/` marker JSON describing a transcription failure."""
    key = failed_transcript_key_for(memo_key)
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 transcript-failure write failed for {key!r}: {e}") from e
    return key


def get_transcript(memo_key: str) -> dict | None:
    """Load a transcript JSON; return None if it doesn't exist yet."""
    key = transcript_key_for(memo_key)
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return json.loads(response["Body"].read())


def head_transcript_status_parallel(
    memo_keys: list[str], max_workers: int = 10
) -> dict[str, str]:
    """HEAD each memo's transcript + `.failed/` marker; return status map.

    Returned map: memo_key -> one of `transcribed | failed | pending`.
    Missing transcripts (404 on both) come back as `pending`.
    """
    if not memo_keys:
        return {}
    client = get_s3_client()
    bucket = settings.b2_bucket_name

    def _check(memo_key: str) -> tuple[str, str]:
        # Success path first — most memos are expected to land here.
        try:
            client.head_object(Bucket=bucket, Key=transcript_key_for(memo_key))
            return memo_key, "transcribed"
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchKey"):
                raise
        try:
            client.head_object(
                Bucket=bucket, Key=failed_transcript_key_for(memo_key)
            )
            return memo_key, "failed"
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchKey"):
                raise
        return memo_key, "pending"

    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for memo_key, status in pool.map(_check, memo_keys):
            out[memo_key] = status
    return out


def delete_transcript(memo_key: str) -> None:
    """Best-effort delete of a memo's transcript + `.failed/` marker."""
    client = get_s3_client()
    bucket = settings.b2_bucket_name
    for key in (transcript_key_for(memo_key), failed_transcript_key_for(memo_key)):
        try:
            client.delete_object(Bucket=bucket, Key=key)
        except ClientError:
            # Missing siblings are fine; we never created one for this memo.
            continue

"""B2 helpers for the `tags/` prefix.

Each tags artifact is a JSON document at `tags/<YYYY>/<MM>/<stem>.json`
that mirrors the source memo's date-partitioned key shape.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.b2_transcripts import _stem_for_memo_key

TAGS_PREFIX = "tags/"


def tags_key_for(memo_key: str) -> str:
    """Compute the canonical tags JSON key for a memo."""
    return f"{TAGS_PREFIX}{_stem_for_memo_key(memo_key)}.json"


def put_tags(memo_key: str, payload: dict) -> str:
    """Write a tags JSON; return the resulting key."""
    key = tags_key_for(memo_key)
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 tags write failed for {key!r}: {e}") from e
    return key


def get_tags(memo_key: str) -> dict | None:
    """Load a tags JSON; return None if it doesn't exist yet."""
    key = tags_key_for(memo_key)
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return json.loads(response["Body"].read())


def get_tags_parallel(
    memo_keys: list[str], max_workers: int = 10
) -> dict[str, list[str]]:
    """Fetch the `tags` array for each memo (empty list when missing)."""
    if not memo_keys:
        return {}
    client = get_s3_client()
    bucket = settings.b2_bucket_name

    def _one(memo_key: str) -> tuple[str, list[str]]:
        try:
            response = client.get_object(
                Bucket=bucket, Key=tags_key_for(memo_key)
            )
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return memo_key, []
            raise
        payload = json.loads(response["Body"].read())
        return memo_key, list(payload.get("tags", []))

    out: dict[str, list[str]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for memo_key, tags in pool.map(_one, memo_keys):
            out[memo_key] = tags
    return out


def delete_tags(memo_key: str) -> None:
    """Best-effort delete of a memo's tags JSON."""
    client = get_s3_client()
    try:
        client.delete_object(
            Bucket=settings.b2_bucket_name, Key=tags_key_for(memo_key)
        )
    except ClientError:
        return

"""B2 helpers for the `summaries/` prefix.

Daily summaries land at `summaries/<YYYY>/<DD>.md` and weekly summaries at
`summaries/<YYYY>/W<WW>.md`. A small JSON sidecar
(`summaries/<YYYY>/<DD>.json`) carries the metadata the listing endpoint
needs without re-parsing every markdown blob.
"""

from __future__ import annotations

import json

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

SUMMARIES_PREFIX = "summaries/"


def daily_summary_key(year: int, day_iso: str) -> str:
    """`summaries/<YYYY>/<YYYY-MM-DD>.md`."""
    return f"{SUMMARIES_PREFIX}{year:04d}/{day_iso}.md"


def weekly_summary_key(year: int, week: int) -> str:
    """`summaries/<YYYY>/W<WW>.md` (ISO week, zero-padded)."""
    return f"{SUMMARIES_PREFIX}{year:04d}/W{week:02d}.md"


def sidecar_key_for(summary_key: str) -> str:
    """Return the JSON sidecar key for a given markdown summary key."""
    if summary_key.endswith(".md"):
        return summary_key[: -len(".md")] + ".json"
    return summary_key + ".json"


def put_summary(summary_key: str, markdown: str, sidecar: dict) -> str:
    """Write a markdown summary + JSON sidecar to B2."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=summary_key,
            Body=markdown.encode("utf-8"),
            ContentType="text/markdown; charset=utf-8",
        )
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=sidecar_key_for(summary_key),
            Body=json.dumps(sidecar, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
    except ClientError as e:
        raise RuntimeError(
            f"B2 summary write failed for {summary_key!r}: {e}"
        ) from e
    return summary_key


def get_summary(summary_key: str) -> tuple[str | None, dict | None]:
    """Load a summary's markdown body and JSON sidecar.

    Returns `(markdown, sidecar)`. Either side may be None if missing.
    """
    client = get_s3_client()
    bucket = settings.b2_bucket_name

    markdown: str | None = None
    sidecar: dict | None = None

    try:
        response = client.get_object(Bucket=bucket, Key=summary_key)
        markdown = response["Body"].read().decode("utf-8")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("404", "NoSuchKey"):
            raise

    try:
        response = client.get_object(
            Bucket=bucket, Key=sidecar_key_for(summary_key)
        )
        sidecar = json.loads(response["Body"].read())
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("404", "NoSuchKey"):
            raise

    return markdown, sidecar


def list_summary_sidecars(max_keys: int = 1000) -> list[dict]:
    """Return every sidecar JSON under `summaries/`, newest-first.

    The sidecar carries all metadata the listing UI needs; we never have to
    fetch the markdown body for a list render.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": SUMMARIES_PREFIX,
        "MaxKeys": 1000,
    }
    fetched = 0
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                if not obj["Key"].endswith(".json"):
                    continue
                try:
                    body = client.get_object(
                        Bucket=settings.b2_bucket_name, Key=obj["Key"]
                    )["Body"].read()
                    payload = json.loads(body)
                except ClientError:
                    continue
                out.append(payload)
                fetched += 1
                if fetched >= max_keys:
                    return out
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 summaries list failed: {e}") from e
    return out


def delete_summary(summary_key: str) -> None:
    """Best-effort delete of a summary markdown + its sidecar."""
    client = get_s3_client()
    bucket = settings.b2_bucket_name
    for key in (summary_key, sidecar_key_for(summary_key)):
        try:
            client.delete_object(Bucket=bucket, Key=key)
        except ClientError:
            continue

"""B2 helpers for the `embeddings/` prefix.

Each embedding artifact is a JSON document at
`embeddings/<YYYY>/<MM>/<stem>.json` carrying a `vector` array. For v1 we
load all embeddings into memory at query time and run cosine in-process —
suitable for thousands of memos; a vector index is documented as v2.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.b2_transcripts import _stem_for_memo_key

EMBEDDINGS_PREFIX = "embeddings/"


def embedding_key_for(memo_key: str) -> str:
    """Compute the canonical embedding JSON key for a memo."""
    return f"{EMBEDDINGS_PREFIX}{_stem_for_memo_key(memo_key)}.json"


def put_embedding(memo_key: str, payload: dict) -> str:
    """Write an embedding JSON; return the resulting key."""
    key = embedding_key_for(memo_key)
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json; charset=utf-8",
        )
    except ClientError as e:
        raise RuntimeError(f"B2 embedding write failed for {key!r}: {e}") from e
    return key


def get_embedding(memo_key: str) -> dict | None:
    """Load an embedding JSON; return None if it doesn't exist yet."""
    key = embedding_key_for(memo_key)
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise
    return json.loads(response["Body"].read())


def list_embedding_keys(max_keys: int = 10_000) -> list[str]:
    """List every embedding object key (full bucket scan of the prefix)."""
    client = get_s3_client()
    out: list[str] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": EMBEDDINGS_PREFIX,
        "MaxKeys": 1000,
    }
    fetched = 0
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                out.append(obj["Key"])
                fetched += 1
                if fetched >= max_keys:
                    return out
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 embeddings list failed: {e}") from e
    return out


def get_embeddings_parallel(
    embedding_keys: list[str], max_workers: int = 10
) -> dict[str, list[float]]:
    """Load every embedding vector keyed by the embedding object key."""
    if not embedding_keys:
        return {}
    client = get_s3_client()
    bucket = settings.b2_bucket_name

    def _one(key: str) -> tuple[str, list[float]]:
        try:
            response = client.get_object(Bucket=bucket, Key=key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return key, []
            raise
        payload = json.loads(response["Body"].read())
        return key, list(payload.get("vector", []))

    out: dict[str, list[float]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for key, vec in pool.map(_one, embedding_keys):
            if vec:
                out[key] = vec
    return out


def delete_embedding(memo_key: str) -> None:
    """Best-effort delete of a memo's embedding JSON."""
    client = get_s3_client()
    try:
        client.delete_object(
            Bucket=settings.b2_bucket_name, Key=embedding_key_for(memo_key)
        )
    except ClientError:
        return

"""B2 helpers scoped to the memo (raw audio) prefix.

Voice memos are the primary surface of this sample; these helpers sit
alongside `b2_client.py` so the generic explorer keeps its independent
listing / head / delete helpers while the memo path can grow extra
affordances (parallel HEAD, playback presign) without bloating the file.
"""

from concurrent.futures import ThreadPoolExecutor

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client

# Memos store raw audio under `audio/`. Derived artifacts live alongside
# under their own prefixes (see `repo/b2_transcripts.py` etc.). `AUDIO_PREFIX`
# is the canonical name; `MEMO_PREFIX` is an alias kept for clarity at the
# service-layer call sites that talk about "memos".
AUDIO_PREFIX = "audio/"
MEMO_PREFIX = AUDIO_PREFIX


def list_audio_objects(max_keys: int = 1000) -> list[dict]:
    """List raw S3 objects under the audio prefix.

    Returned dicts contain at least: Key, Size, LastModified. Callers in
    service/ shape these into Memo models — repo stays a thin data-access
    layer.

    Raises RuntimeError on S3 failure.
    """
    client = get_s3_client()
    contents: list[dict] = []
    kwargs: dict = {
        "Bucket": settings.b2_bucket_name,
        "Prefix": AUDIO_PREFIX,
        "MaxKeys": max_keys,
    }
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            contents.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 audio list failed: {e}") from e
    return contents


def get_audio_bytes(key: str) -> tuple[bytes, str]:
    """Fetch an audio object's raw bytes + content type.

    Returns `(body, content_type)`. Raises RuntimeError on B2 failure (so the
    transcription pipeline can write a `.failed/` marker instead of crashing).
    """
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 audio fetch failed for {key!r}: {e}") from e
    return (
        response["Body"].read(),
        response.get("ContentType", "application/octet-stream"),
    )


def head_audio_object(key: str) -> dict | None:
    """Return the raw head_object response for an audio key, or None if missing."""
    client = get_s3_client()
    try:
        return client.head_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise


def head_audio_objects_parallel(
    keys: list[str], max_workers: int = 10
) -> dict[str, dict]:
    """Issue HEAD for each key in parallel; map key -> head response.

    Missing keys (404) are silently dropped — list_objects_v2 can race a
    concurrent delete, and a missing aggregate entry is preferable to a
    500 on the dashboard. Other errors bubble up.
    """
    if not keys:
        return {}
    client = get_s3_client()
    bucket = settings.b2_bucket_name

    def _one(key: str) -> tuple[str, dict | None]:
        try:
            return key, client.head_object(Bucket=bucket, Key=key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey"):
                return key, None
            raise

    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for key, head in pool.map(_one, keys):
            if head is not None:
                out[key] = head
    return out


def delete_audio_object(key: str) -> None:
    """Delete an audio object. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.delete_object(Bucket=settings.b2_bucket_name, Key=key)
    except ClientError as e:
        raise RuntimeError(f"B2 audio delete failed for '{key}': {e}") from e


def delete_audio_objects_batch(keys: list[str]) -> tuple[list[str], list[dict]]:
    """Batch-delete audio assets via S3 DeleteObjects.

    Mirrors `b2_client.delete_files_batch` but kept on the audio side so the
    Library never reaches into the generic explorer's helpers.

    Returns `(deleted_keys, errors)`; an empty input is a no-op.
    Raises RuntimeError on a transport-level failure.
    """
    if not keys:
        return [], []
    client = get_s3_client()
    deleted: list[str] = []
    errors: list[dict] = []
    for i in range(0, len(keys), 1000):
        chunk = keys[i : i + 1000]
        try:
            response = client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": False},
            )
        except ClientError as e:
            raise RuntimeError(f"B2 audio batch delete failed: {e}") from e
        deleted.extend(d["Key"] for d in response.get("Deleted", []))
        for err in response.get("Errors", []):
            errors.append(
                {
                    "Key": err.get("Key", ""),
                    "Code": err.get("Code", ""),
                    "Message": err.get("Message", ""),
                }
            )
    return deleted, errors


def presign_audio_playback(key: str, expires_in: int = 600) -> str:
    """Inline-playback presigned GET (no Content-Disposition: attachment)."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e

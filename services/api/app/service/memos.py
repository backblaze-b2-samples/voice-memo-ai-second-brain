"""Memo service layer.

Lists, heads, deletes, and presigns voice-memo audio assets stored under the
`audio/` prefix in B2 plus their sibling artifacts (transcripts, tags,
embeddings). The service layer owns key validation and pipeline-status
derivation; raw S3 calls live in `repo/b2_audio.py` and the sibling repo
modules.

The canonical shape produced by the Upload pipeline is
`audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>`, but the memo listing plays
any object under `audio/` ending in a supported extension — files seeded
into the bucket via the B2 console, an earlier sample, or direct S3 sync
stay playable. The `--<uuid>` suffix is stripped for display via
`_filename_from_key`; externally-seeded keys with no `--` are shown as-is.
"""

from __future__ import annotations

import logging
import mimetypes
import re

from app.repo import (
    MEMO_PREFIX,
    delete_audio_object,
    delete_audio_objects_batch,
    delete_embedding,
    delete_tags,
    delete_transcript,
    get_presigned_url,
    get_tags_parallel,
    head_audio_object,
    head_audio_objects_parallel,
    head_transcript_status_parallel,
    list_audio_objects,
    presign_audio_playback,
)
from app.types import Memo
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

# Memos live under the `audio/` prefix and end in a supported extension.
# Path-traversal payloads and unknown extensions are rejected before any
# B2 call.
MEMO_KEY_RE = re.compile(
    r"^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus|webm)$",
    re.IGNORECASE,
)


class MemoKeyError(Exception):
    """Raised when a memo key is malformed."""

    def __init__(self, detail: str = "Invalid memo key"):
        self.detail = detail
        super().__init__(detail)


class MemoNotFound(Exception):
    """Raised when no memo exists at the requested key."""

    def __init__(self, detail: str = "Memo not found"):
        self.detail = detail
        super().__init__(detail)


def validate_memo_key(key: str) -> None:
    """Reject keys that don't match the memo prefix shape."""
    if not key or ".." in key or "//" in key or not MEMO_KEY_RE.match(key):
        raise MemoKeyError()


def _guess_codec(key: str) -> str | None:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return ext or None


def _content_type_for(key: str) -> str:
    mime, _ = mimetypes.guess_type(key)
    return mime or "application/octet-stream"


def _filename_from_key(key: str) -> str:
    """Return the human-readable filename embedded in a key."""
    segment = key.rsplit("/", 1)[-1]
    if "--" not in segment:
        return segment
    if "." in segment:
        body, _, ext = segment.rpartition(".")
        stem, sep, _ = body.rpartition("--")
        if not sep:
            return segment
        return f"{stem}.{ext}" if stem else segment
    stem, sep, _ = segment.rpartition("--")
    return stem if sep and stem else segment


def _int_or_none(v: object) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _metadata_from_head(head: dict | None) -> dict:
    if not head:
        return {}
    meta = head.get("Metadata") or {}
    return {
        "duration_ms": _int_or_none(meta.get("duration-ms")),
        "sample_rate": _int_or_none(meta.get("sample-rate")),
        "channels": _int_or_none(meta.get("channels")),
        "bit_depth": _int_or_none(meta.get("bit-depth")),
        "codec": meta.get("codec") or None,
    }


def _memo_from_object(obj: dict, head: dict | None = None) -> Memo:
    key = obj["Key"]
    size = obj["Size"]
    extra = _metadata_from_head(head)
    if not extra.get("codec"):
        extra["codec"] = _guess_codec(key)
    return Memo(
        key=key,
        size_bytes=size,
        size_human=humanize_bytes(size),
        content_type=_content_type_for(key),
        created_at=obj["LastModified"],
        title_preview=_filename_from_key(key),
        **extra,
    )


def list_memos(
    limit: int = 100,
    with_metadata: bool = True,
    with_pipeline_status: bool = True,
) -> list[Memo]:
    """List memos, newest-first, optionally annotating pipeline status.

    `with_metadata` performs the existing parallel HEAD that surfaces
    duration / sample rate / etc. `with_pipeline_status` additionally
    HEADs `transcripts/<stem>.json` (and `transcripts/.failed/<stem>.json`)
    so the UI can show "pending | transcribed | failed" badges without a
    separate roundtrip. Pass `False` to keep listing cheap on big buckets.
    """
    if limit < 1 or limit > 500:
        raise ValueError("Limit must be between 1 and 500")
    raw = list_audio_objects(max_keys=1000)
    raw.sort(key=lambda o: o["LastModified"], reverse=True)
    raw = raw[:limit]

    heads: dict[str, dict] = (
        head_audio_objects_parallel([obj["Key"] for obj in raw])
        if with_metadata
        else {}
    )
    statuses: dict[str, str] = (
        head_transcript_status_parallel([obj["Key"] for obj in raw])
        if with_pipeline_status
        else {}
    )
    tag_map: dict[str, list[str]] = (
        get_tags_parallel([obj["Key"] for obj in raw])
        if with_pipeline_status
        else {}
    )

    memos: list[Memo] = []
    for obj in raw:
        memo = _memo_from_object(obj, heads.get(obj["Key"]))
        if with_pipeline_status:
            status = statuses.get(obj["Key"], "pending")
            memo = memo.model_copy(
                update={
                    "transcription_status": status,
                    "tags": tag_map.get(obj["Key"]) or [],
                }
            )
        memos.append(memo)
    return memos




def get_playback_url(key: str) -> str:
    """Return an inline presigned GET (no Content-Disposition)."""
    validate_memo_key(key)
    if head_audio_object(key) is None:
        raise MemoNotFound()
    return presign_audio_playback(key)


def get_download_url(key: str) -> str:
    """Return a presigned GET with `Content-Disposition: attachment`."""
    validate_memo_key(key)
    head = head_audio_object(key)
    if head is None:
        raise MemoNotFound()
    return get_presigned_url(key, filename=_filename_from_key(key))


def delete_memo(key: str) -> None:
    """Validate the key and delete the memo + every sibling artifact.

    The pipeline writes transcripts/, tags/, and embeddings/ siblings under
    keys derived from the memo's date+stem. We tear each down on delete so
    a deleted memo doesn't leave dangling references in the related-memos
    cosine search or in the summary cache.
    """
    validate_memo_key(key)
    delete_audio_object(key)
    delete_transcript(key)
    delete_tags(key)
    delete_embedding(key)


def bulk_delete_memos(keys: list[str]) -> tuple[list[str], list[dict]]:
    """Validate each memo key and batch-delete via S3 DeleteObjects."""
    if not keys:
        raise MemoKeyError("No keys provided")
    if len(keys) > 1000:
        raise MemoKeyError("Cannot delete more than 1000 keys per request")
    seen: set[str] = set()
    cleaned: list[str] = []
    for k in keys:
        validate_memo_key(k)
        if k not in seen:
            seen.add(k)
            cleaned.append(k)
    deleted, errors = delete_audio_objects_batch(cleaned)
    for k in deleted:
        delete_transcript(k)
        delete_tags(k)
        delete_embedding(k)
    return deleted, errors


def get_memo_aggregates() -> dict:
    """Return memo-aware aggregates for the dashboard endpoint."""
    raw = list_audio_objects(max_keys=10_000)
    total = len(raw)
    total_size = sum(obj["Size"] for obj in raw)

    keys = [obj["Key"] for obj in raw]
    heads = head_audio_objects_parallel(keys) if keys else {}
    statuses = head_transcript_status_parallel(keys) if keys else {}

    total_duration_ms = 0
    formats: dict[str, int] = {}
    transcribed = pending = failed = 0
    for obj in raw:
        ext = _guess_codec(obj["Key"]) or "other"
        formats[ext] = formats.get(ext, 0) + 1
        head = heads.get(obj["Key"])
        if head is not None:
            dur = _int_or_none((head.get("Metadata") or {}).get("duration-ms"))
            if dur:
                total_duration_ms += dur
        status = statuses.get(obj["Key"], "pending")
        if status == "transcribed":
            transcribed += 1
        elif status == "failed":
            failed += 1
        else:
            pending += 1

    return {
        "total_memos": total,
        "total_audio_assets": total,
        "total_duration_ms": total_duration_ms,
        "total_size_bytes": total_size,
        "total_size_human": humanize_bytes(total_size),
        "audio_prefix": MEMO_PREFIX,
        "formats": formats,
        "transcribed_count": transcribed,
        "pending_count": pending,
        "failed_count": failed,
    }



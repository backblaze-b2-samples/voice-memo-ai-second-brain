from pydantic import BaseModel


class DailyUploadCount(BaseModel):
    date: str
    uploads: int
    duration_ms: int = 0


class UploadStats(BaseModel):
    """Memo-centric dashboard metrics.

    Mirrors the shape consumed by `apps/web/src/components/dashboard/*`.
    `total_files` / `total_size_*` cover everything in the bucket so the
    underlying explorer keeps working; `total_memos`, `total_duration_ms`,
    `transcribed_count`, and `pending_count` surface the metrics the
    dashboard tiles actually render. `formats` is a sparse map of
    extension -> count (e.g. {"wav": 5, "mp3": 12}). `total_audio_assets`
    is kept as an alias of `total_memos` so older callers don't crash.
    """

    total_files: int
    total_size_bytes: int
    total_size_human: str
    uploads_today: int
    total_downloads: int
    # Memo-aware aggregates
    total_memos: int = 0
    total_audio_assets: int = 0
    total_duration_ms: int = 0
    audio_size_bytes: int = 0
    audio_size_human: str = "0 B"
    formats: dict[str, int] = {}
    # Pipeline status aggregates (derived by HEAD-checking transcripts/).
    transcribed_count: int = 0
    pending_count: int = 0
    failed_count: int = 0

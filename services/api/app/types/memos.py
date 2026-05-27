from datetime import datetime
from typing import Literal

from pydantic import BaseModel

TranscriptionStatus = Literal["pending", "transcribed", "failed"]


class Memo(BaseModel):
    """A voice memo stored under the `audio/` prefix in B2.

    Sourced entirely from S3 list/head responses — no application database.
    Pipeline-derived fields (`transcription_status`, `tags`,
    `embedding_present`) are computed by HEAD-checking sibling objects under
    the `transcripts/`, `tags/`, and `embeddings/` prefixes.
    """

    key: str
    size_bytes: int
    size_human: str
    content_type: str
    created_at: datetime
    # Audio-specific (populated by service/audio_metadata.py when present).
    duration_ms: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_depth: int | None = None
    codec: str | None = None
    # Filename shown in card header; derived from the last path segment.
    title_preview: str | None = None
    # Pipeline-derived fields. None when the pipeline-status query was
    # skipped (e.g. detail-only fetches that don't HEAD siblings).
    transcription_status: TranscriptionStatus | None = None
    tags: list[str] | None = None
    transcript_preview: str | None = None
    embedding_present: bool | None = None

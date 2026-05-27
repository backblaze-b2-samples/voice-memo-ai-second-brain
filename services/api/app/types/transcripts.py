from datetime import datetime

from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """A single Whisper transcript segment with timestamps in seconds."""

    start: float
    end: float
    text: str


class Transcript(BaseModel):
    """A transcript JSON stored under `transcripts/<YYYY>/<MM>/<stem>.json`.

    The shape mirrors a slimmed-down Whisper verbose JSON response: a full
    `text` field plus `segments` carrying word-level timestamps so the memo
    detail page can render timestamp anchors.
    """

    memo_key: str
    text: str
    segments: list[TranscriptSegment] = []
    language: str | None = None
    model: str | None = None
    generated_at: datetime

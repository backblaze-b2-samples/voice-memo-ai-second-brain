"""Transcription pipeline.

Orchestrates: fetch a memo's bytes from B2 -> POST to Whisper -> write the
resulting transcript JSON to `transcripts/<stem>.json` or, on failure, write
`transcripts/.failed/<stem>.json`. Designed to be invoked from a FastAPI
BackgroundTasks callback right after a successful upload.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    get_audio_bytes,
    head_audio_object,
    put_failed_marker,
    put_transcript,
)
from app.repo.transcription_client import (
    TranscriptionClientError,
    transcribe,
)
from app.service.memos import _filename_from_key, validate_memo_key
from app.types import Transcript, TranscriptSegment

logger = logging.getLogger(__name__)


def transcribe_memo(memo_key: str) -> Transcript:
    """Run Whisper on a memo's audio and persist the transcript JSON.

    Raises TranscriptionClientError when the API call itself fails — the
    caller (background-task wrapper) catches that to write the `.failed/`
    marker. Returns the structured Transcript on success.
    """
    validate_memo_key(memo_key)
    if head_audio_object(memo_key) is None:
        raise FileNotFoundError(f"Memo not found in B2: {memo_key!r}")

    audio_bytes, content_type = get_audio_bytes(memo_key)
    raw = transcribe(audio_bytes, _filename_from_key(memo_key), content_type)

    segments = [
        TranscriptSegment(
            start=float(s.get("start", 0.0)),
            end=float(s.get("end", 0.0)),
            text=str(s.get("text", "")).strip(),
        )
        for s in raw.get("segments", [])
    ]
    transcript = Transcript(
        memo_key=memo_key,
        text=str(raw.get("text", "")).strip(),
        segments=segments,
        language=raw.get("language"),
        model=settings.openai_transcription_model,
        generated_at=datetime.now(UTC),
    )
    put_transcript(memo_key, transcript.model_dump(mode="json"))
    return transcript


def run(memo_key: str) -> None:
    """Background-task entrypoint — never raises.

    On success: writes `transcripts/<stem>.json` and fans out to the
    tagging + embedding tasks. On failure: writes `transcripts/.failed/`
    so the UI status can flip to `failed`.
    """
    try:
        transcribe_memo(memo_key)
    except TranscriptionClientError as e:
        logger.warning("Transcription failed for %s: %s", memo_key, e)
        try:
            put_failed_marker(
                memo_key,
                {
                    "memo_key": memo_key,
                    "error": str(e),
                    "failed_at": datetime.now(UTC).isoformat(),
                },
            )
        except RuntimeError:
            logger.exception("Failed to write `.failed/` marker for %s", memo_key)
        return
    except Exception:
        logger.exception("Transcription pipeline crashed for %s", memo_key)
        return

    # Fan out to downstream stages. Imported locally to avoid a circular
    # import (tagging + related_memos both reference transcripts).
    from app.service import related_memos, tagging

    try:
        tagging.run(memo_key)
    except Exception:
        logger.exception("Tagging stage crashed for %s", memo_key)
    try:
        related_memos.embed_memo(memo_key)
    except Exception:
        logger.exception("Embedding stage crashed for %s", memo_key)

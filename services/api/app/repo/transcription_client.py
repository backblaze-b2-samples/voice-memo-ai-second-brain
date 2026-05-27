"""OpenAI Whisper HTTP client.

Wraps the `POST /v1/audio/transcriptions` endpoint via `httpx`. We keep the
SDK contained in `repo/` per the layering invariant — the service layer
only sees the normalized `dict` return value. The model is configurable via
`OPENAI_TRANSCRIPTION_MODEL`.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"


class TranscriptionClientError(RuntimeError):
    """Raised when the OpenAI transcription API returns an error."""


def transcribe(
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    timeout_s: float = 60.0,
) -> dict:
    """Transcribe an audio blob with OpenAI Whisper.

    Returns the verbose JSON payload (`text`, `segments`, `language`).
    Raises TranscriptionClientError on HTTP errors so the service layer can
    write a `.failed/` marker.
    """
    if not settings.openai_api_key:
        raise TranscriptionClientError(
            "OPENAI_API_KEY is not set — cannot transcribe. Add it to .env."
        )

    files = {
        "file": (filename, audio_bytes, content_type),
    }
    data = {
        "model": settings.openai_transcription_model,
        "response_format": "verbose_json",
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                OPENAI_TRANSCRIPTIONS_URL,
                headers=headers,
                files=files,
                data=data,
            )
    except httpx.HTTPError as e:
        raise TranscriptionClientError(f"transcription HTTP error: {e}") from e

    if response.status_code >= 400:
        raise TranscriptionClientError(
            f"transcription failed: {response.status_code} {response.text[:500]}"
        )
    return response.json()

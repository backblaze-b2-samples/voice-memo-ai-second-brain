"""OpenAI embeddings client.

Wraps `POST /v1/embeddings`. The model is configurable via
`OPENAI_EMBEDDING_MODEL` (default `text-embedding-3-small`).
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"


class EmbeddingsClientError(RuntimeError):
    """Raised when the OpenAI embeddings API returns an error."""


def embed(text: str, timeout_s: float = 30.0) -> list[float]:
    """Return the embedding vector for a single input string."""
    if not settings.openai_api_key:
        raise EmbeddingsClientError(
            "OPENAI_API_KEY is not set — cannot compute embeddings."
        )

    payload = {
        "model": settings.openai_embedding_model,
        "input": text,
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                OPENAI_EMBEDDINGS_URL, headers=headers, json=payload
            )
    except httpx.HTTPError as e:
        raise EmbeddingsClientError(f"embeddings HTTP error: {e}") from e

    if response.status_code >= 400:
        raise EmbeddingsClientError(
            f"embeddings failed: {response.status_code} {response.text[:500]}"
        )
    body = response.json()
    try:
        return list(body["data"][0]["embedding"])
    except (KeyError, IndexError, TypeError) as e:
        raise EmbeddingsClientError(
            f"embeddings response missing vector: {body}"
        ) from e

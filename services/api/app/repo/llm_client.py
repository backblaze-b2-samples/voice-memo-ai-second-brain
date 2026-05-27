"""OpenAI chat client.

Wraps `POST /v1/chat/completions`. Used by the tagging service for
keyword/tag extraction and by the summaries service for daily/weekly
rollups. The model is configurable via `OPENAI_CHAT_MODEL`.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"


class LlmClientError(RuntimeError):
    """Raised when the OpenAI chat API returns an error."""


def chat_completion(
    messages: list[dict],
    response_format: dict | None = None,
    temperature: float = 0.2,
    timeout_s: float = 60.0,
) -> str:
    """Issue a chat completion and return the assistant's content string."""
    if not settings.openai_api_key:
        raise LlmClientError(
            "OPENAI_API_KEY is not set — cannot call chat completions."
        )

    payload: dict = {
        "model": settings.openai_chat_model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_format is not None:
        payload["response_format"] = response_format
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.post(
                OPENAI_CHAT_URL, headers=headers, json=payload
            )
    except httpx.HTTPError as e:
        raise LlmClientError(f"chat HTTP error: {e}") from e

    if response.status_code >= 400:
        raise LlmClientError(
            f"chat failed: {response.status_code} {response.text[:500]}"
        )
    body = response.json()
    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise LlmClientError(f"chat response missing content: {body}") from e

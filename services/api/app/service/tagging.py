"""Tagging pipeline.

Loads a memo's transcript text -> asks the LLM for tags / topics / entities
in strict JSON -> writes `tags/<stem>.json`. Invoked from the transcription
service's fan-out step after a successful transcription.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from app.config import settings
from app.repo import get_transcript, put_tags
from app.repo.llm_client import LlmClientError, chat_completion
from app.service.memos import validate_memo_key
from app.types import MemoTags

logger = logging.getLogger(__name__)

# Cap the transcript window we feed to the chat model — voice memos are
# short, but we still bound this so the prompt cost stays predictable on
# the occasional 30-min memo.
MAX_TRANSCRIPT_CHARS = 12_000

SYSTEM_PROMPT = (
    "You extract concise metadata from spoken voice memos. "
    "Reply ONLY with a JSON object containing three string arrays: "
    "`tags` (max 8, lowercase, single words or short phrases), "
    "`topics` (max 5, short noun phrases), and "
    "`entities` (max 8, named people/places/products mentioned). "
    "Return an empty array when nothing applies."
)


def _build_messages(text: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Transcript:\n\"\"\"\n{text}\n\"\"\""},
    ]


def _parse_response(raw: str) -> dict:
    """Parse a JSON-object reply; tolerate extra text around the JSON block."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fall back to extracting the first {...} block.
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(raw[start : end + 1])


def _normalize_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            s = item.strip().lower()
            if s:
                out.append(s)
    return out


def tag_memo(memo_key: str) -> MemoTags:
    """Run the LLM tagger against a memo's transcript and persist the result."""
    validate_memo_key(memo_key)
    transcript = get_transcript(memo_key)
    if not transcript:
        raise FileNotFoundError(
            f"No transcript at {memo_key!r}; run transcription first."
        )
    text = str(transcript.get("text", "")).strip()
    if not text:
        # Nothing to tag — write an empty record so the UI status is stable.
        tags = MemoTags(
            memo_key=memo_key,
            tags=[],
            topics=[],
            entities=[],
            model=settings.openai_chat_model,
            generated_at=datetime.now(UTC),
        )
        put_tags(memo_key, tags.model_dump(mode="json"))
        return tags

    text = text[:MAX_TRANSCRIPT_CHARS]
    raw_reply = chat_completion(
        _build_messages(text),
        response_format={"type": "json_object"},
    )
    parsed = _parse_response(raw_reply)
    tags = MemoTags(
        memo_key=memo_key,
        tags=_normalize_list(parsed.get("tags")),
        topics=_normalize_list(parsed.get("topics")),
        entities=_normalize_list(parsed.get("entities")),
        model=settings.openai_chat_model,
        generated_at=datetime.now(UTC),
    )
    put_tags(memo_key, tags.model_dump(mode="json"))
    return tags


def run(memo_key: str) -> None:
    """Background-task entrypoint — swallows errors and logs."""
    try:
        tag_memo(memo_key)
    except LlmClientError as e:
        logger.warning("Tagging failed for %s: %s", memo_key, e)
    except Exception:
        logger.exception("Tagging pipeline crashed for %s", memo_key)

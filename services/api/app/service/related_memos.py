"""Cross-reference (embeddings) pipeline + related-memos search.

Two responsibilities, kept in one file because they share the embedding
key-derivation helpers:

1. `embed_memo(memo_key)` — fan-out step from the transcription pipeline.
   Loads the transcript text, calls the embeddings API, writes
   `embeddings/<stem>.json`.
2. `find_related(memo_key, top_k)` — service-level query for the
   `GET /memos/{key}/related` endpoint. Loads all embeddings in process
   and ranks by cosine. Naïve for v1; documented v2 path in
   `docs/features/cross-references.md`.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime

from app.config import settings
from app.repo import (
    embedding_key_for,
    get_embedding,
    get_embeddings_parallel,
    get_transcript,
    list_embedding_keys,
    put_embedding,
)
from app.repo.embeddings_client import EmbeddingsClientError, embed
from app.service.memos import _filename_from_key, validate_memo_key
from app.types import RelatedMemo

logger = logging.getLogger(__name__)

# Cap the transcript window we embed — embedding models also have token
# limits, and a single long memo dominating cosine ranks isn't what we want.
MAX_EMBED_CHARS = 8_000


def _memo_key_from_embedding_key(embedding_key: str) -> str:
    """Inverse of `embedding_key_for`. Returns the source memo key."""
    # embeddings/<YYYY>/<MM>/<stem>.json -> audio/<YYYY>/<MM>/<stem>
    # We don't recover the audio extension from the embedding key, so we
    # return the stem-prefixed key without an extension. Callers that need
    # the real audio key should look up by stem via the memo list.
    if not embedding_key.startswith("embeddings/"):
        return embedding_key
    body = embedding_key[len("embeddings/") :]
    if body.endswith(".json"):
        body = body[: -len(".json")]
    return f"audio/{body}"


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_memo(memo_key: str) -> list[float]:
    """Embed a memo's transcript and persist `embeddings/<stem>.json`."""
    validate_memo_key(memo_key)
    transcript = get_transcript(memo_key)
    if not transcript:
        raise FileNotFoundError(
            f"No transcript at {memo_key!r}; run transcription first."
        )
    text = str(transcript.get("text", "")).strip()
    if not text:
        logger.info("Skipping embedding for empty transcript: %s", memo_key)
        return []

    vector = embed(text[:MAX_EMBED_CHARS])
    payload = {
        "memo_key": memo_key,
        "vector": vector,
        "model": settings.openai_embedding_model,
        "dim": len(vector),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    put_embedding(memo_key, payload)
    return vector


def find_related(memo_key: str, top_k: int = 5) -> list[RelatedMemo]:
    """Rank every other memo by cosine similarity to `memo_key`'s embedding.

    Returns the top-K results, excluding the source memo itself. If the
    source memo has no embedding (transcription still running, or
    embedding stage failed), returns an empty list rather than raising —
    the UI handles the empty case gracefully.
    """
    validate_memo_key(memo_key)
    source = get_embedding(memo_key)
    if not source:
        return []
    source_vec = list(source.get("vector", []))
    if not source_vec:
        return []

    own_key = embedding_key_for(memo_key)
    all_keys = [k for k in list_embedding_keys() if k != own_key]
    others = get_embeddings_parallel(all_keys)

    scored: list[tuple[str, float]] = []
    for emb_key, vec in others.items():
        score = _cosine(source_vec, vec)
        if score > 0:
            scored.append((emb_key, score))
    scored.sort(key=lambda t: t[1], reverse=True)

    results: list[RelatedMemo] = []
    for emb_key, score in scored[:top_k]:
        related_memo_key = _memo_key_from_embedding_key(emb_key)
        transcript = get_transcript(related_memo_key)
        preview = None
        if transcript:
            preview = str(transcript.get("text", ""))[:160].strip() or None
        results.append(
            RelatedMemo(
                key=related_memo_key,
                score=round(score, 4),
                title_preview=_filename_from_key(related_memo_key),
                transcript_preview=preview,
            )
        )
    return results


def run(memo_key: str) -> None:
    """Background-task entrypoint."""
    try:
        embed_memo(memo_key)
    except EmbeddingsClientError as e:
        logger.warning("Embedding failed for %s: %s", memo_key, e)
    except Exception:
        logger.exception("Embedding pipeline crashed for %s", memo_key)

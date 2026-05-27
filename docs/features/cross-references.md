<!-- last_verified: 2026-05-26 -->
# Feature: Cross-references (related memos)

## Purpose
Rank every other memo by cosine similarity to a given memo's transcript embedding, returning the top-5. Powers the **Related memos** card on the memo detail page.

## Used By
- API: `GET /memos/{key}/related`, background task launched by `service.transcription.run`
- UI: `apps/web/src/components/memos/related-memos.tsx`

## Core Functions
- `services/api/app/service/related_memos.py` — `embed_memo` (pipeline writer) and `find_related` (cosine ranker)
- `services/api/app/repo/embeddings_client.py` — `httpx` wrapper around `POST https://api.openai.com/v1/embeddings`
- `services/api/app/repo/b2_embeddings.py` — `put_embedding`, `get_embedding`, `list_embedding_keys`, `get_embeddings_parallel`, `delete_embedding`

## Canonical Files
- Cosine ranker: `services/api/app/service/related_memos.py::find_related`

## Inputs
- `memo_key`: canonical key
- (writer) the memo's transcript text, truncated to 8,000 chars
- (reader) `top_k`: 1..25 (default 5)

## Outputs
- `embeddings/<YYYY>/<MM>/<stem>.json` containing `{memo_key, vector, model, dim, generated_at}`
- `GET /memos/{key}/related` -> `RelatedMemo[]` with `key`, `score` (cosine), `title_preview`, `transcript_preview`

## Flow
1. After a successful transcript, `service.transcription.run` enqueues `service.related_memos.embed_memo(key)`.
2. `embed_memo` reads the transcript text, calls the embeddings API, writes `embeddings/<stem>.json`.
3. On detail-page load, the UI calls `GET /memos/{key}/related`.
4. `find_related`:
   - Loads the source memo's embedding (returns `[]` if missing).
   - Lists every other key under `embeddings/`.
   - Loads all sibling vectors in parallel.
   - Computes cosine in process, sorts, returns top-K with transcript previews.

## v1 trade-offs / v2 upgrade
- Naïve in-memory cosine is fine for thousands of memos. For tens of thousands, swap `find_related` to talk to a vector index (pgvector, Qdrant, Pinecone) without changing the repo layer's persistence shape.
- Re-embedding all memos when the model changes is a script-level concern (loop `embed_memo`); not yet shipped.

## Edge Cases
- Source memo has no embedding yet -> returns `[]`; UI hides the card.
- Embedding model dimensions mismatch -> `_cosine` returns 0; the memo just doesn't surface as related.
- API quota exhausted -> the writer logs and skips; the user can re-trigger.

## Verification
- Manual: record two memos on the same topic; the detail page should surface each as related to the other within ~10s.
- Quick verify command: `pnpm check:structure`

## Related Docs
- [Transcription](transcription.md)
- [Memo library](memo-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

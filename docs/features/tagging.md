<!-- last_verified: 2026-05-26 -->
# Feature: Tagging

## Purpose
Extract keywords / topics / entities from each memo's transcript via an OpenAI chat call and persist them in B2. Surfaces as chips on `MemoCard` and the detail page.

## Used By
- API: `POST /memos/{key}/retag` (re-queue), background task launched by `service.transcription.run`
- UI: `MemoCard` tag-chip row, `MemoDetail` tags section

## Core Functions
- `services/api/app/service/tagging.py` — `tag_memo(memo_key)` and the `run` wrapper
- `services/api/app/repo/llm_client.py` — `httpx` wrapper around `POST https://api.openai.com/v1/chat/completions`
- `services/api/app/repo/b2_tags.py` — `put_tags`, `get_tags`, `get_tags_parallel`, `delete_tags`
- `services/api/app/types/tags.py` — `MemoTags`

## Canonical Files
- Prompt template + parser: `services/api/app/service/tagging.py`

## Inputs
- `memo_key`: canonical memo key
- The transcript text (loaded from `transcripts/<stem>.json`); truncated to 12,000 chars before the chat call

## Outputs
- `tags/<YYYY>/<MM>/<stem>.json` containing `MemoTags` (`tags`, `topics`, `entities`, `model`, `generated_at`)
- Used by the memo listing's parallel fanout to render tag chips on the card

## Flow
1. Wait for the transcription stage to complete (called from `service.transcription.run` after success).
2. Load `transcripts/<stem>.json`; abort with `FileNotFoundError` if missing.
3. Build a JSON-mode prompt instructing the model to return `{tags[], topics[], entities[]}`.
4. Call `chat_completion(..., response_format={"type": "json_object"})`.
5. Normalize: lowercase, strip empty entries, cap counts (8 tags / 5 topics / 8 entities).
6. Persist via `put_tags`.

## Edge Cases
- Empty transcript -> write an empty record so the UI status is stable.
- LLM response not valid JSON -> fallback to extracting the first `{...}` block; raises if still unparseable.
- `OPENAI_API_KEY` missing -> `LlmClientError`; logged by `run`. No marker is written (tagging is best-effort and the next reupload retries).

## Verification
- Manual: upload a memo with clear content (e.g., "tomorrow I'll write the second-brain post") and confirm tags include `writing`, `second brain`, etc.
- Quick verify command: `pnpm check:structure && pnpm lint:api`

## Related Docs
- [Transcription](transcription.md)
- [Memo library](memo-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

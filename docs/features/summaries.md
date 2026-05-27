<!-- last_verified: 2026-05-26 -->
# Feature: AI summaries (daily / weekly)

## Purpose
On user demand, aggregate transcripts inside a date window, send them to an OpenAI chat completion, and write a markdown summary to B2. Re-requests for the same period return the cached markdown without re-billing the chat API.

## Used By
- UI: `/summary` page
- API: `GET /summaries`, `GET /summaries/{window}/{period}`, `POST /summaries/generate`

## Core Functions
- `services/api/app/service/summaries.py` — `generate_summary`, `list_summaries`, window math
- `services/api/app/repo/b2_summaries.py` — `put_summary`, `get_summary`, `list_summary_sidecars`, `daily_summary_key`, `weekly_summary_key`
- `services/api/app/repo/llm_client.py` — chat completion HTTP wrapper
- `services/api/app/types/summaries.py` — `Summary`, `SummaryListEntry`, `SummaryWindow`

## Canonical Files
- Generation logic: `services/api/app/service/summaries.py::generate_summary`

## Inputs
- `window`: `daily` or `weekly`
- `period`: `YYYY-MM-DD` (daily) or `YYYY-Www` (weekly). Defaults to "today" / "this ISO week" if omitted.
- `force`: when true, bypasses the cache and regenerates.

## Outputs
- Daily: `summaries/<YYYY>/<YYYY-MM-DD>.md` + `summaries/<YYYY>/<YYYY-MM-DD>.json` sidecar
- Weekly: `summaries/<YYYY>/W<WW>.md` + `summaries/<YYYY>/W<WW>.json` sidecar
- The JSON sidecar carries `{key, window, period, memo_count, generated_at, model}` so the listing endpoint does not have to parse markdown.

## Flow
1. Resolve window dates: daily -> `[d, d]`; weekly -> ISO Monday..Sunday.
2. List memos in the window via `list_audio_objects` filtered by `LastModified.date()`.
3. Load transcripts for each memo (skip any with no transcript yet).
4. Build a bundle (capped at 24 KB to bound chat-cost), send to the chat model with a journal-summary system prompt.
5. Persist markdown + sidecar via `put_summary`.
6. Return the `Summary` to the caller.

## Edge Cases
- No transcribed memos in the window -> returns a markdown placeholder ("No transcribed memos in this window yet") and still caches it; this lets the UI show a stable result while the pipeline catches up.
- Cache hit -> skip the chat call entirely; pure B2 GETs.
- LLM call fails -> `LlmClientError`; route returns 502 so the UI can show a toast.

## v1 trade-offs / v2 upgrade
- No scheduler. Daily rollups are user-triggered. A v2 could call `generate_summary` from a cron / Cloud Scheduler entrypoint and pre-fill yesterday/last-week.
- Prompt is hard-coded; swap in `SYSTEM_PROMPT` for richer behavior.

## Verification
- Manual: with a few transcribed memos, hit `Generate` on `/summary` for today.
- Quick verify command: `pnpm check:structure`

## Related Docs
- [Transcription](transcription.md)
- [Memo library](memo-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

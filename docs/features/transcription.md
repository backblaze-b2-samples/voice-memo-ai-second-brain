<!-- last_verified: 2026-06-25 -->
# Feature: Transcription

## Purpose
Turn each new memo into a structured transcript JSON in B2 by calling OpenAI Whisper. Triggered by FastAPI `BackgroundTasks` right after a successful upload; can be re-queued manually for failed memos via `POST /memos/{key}/transcribe`.

## Used By
- API: `POST /memos/{key}/transcribe` (re-queue), background task launched by `runtime/upload.py`
- UI: `MemoStatusBadge` on every card, `TranscriptView` on the detail page

## Core Functions
- `services/api/app/service/transcription.py` — orchestration: fetch audio bytes -> Whisper -> persist JSON; writes a `.failed/` marker on errors
- `services/api/app/repo/transcription_client.py` — thin `httpx` wrapper around `POST https://api.openai.com/v1/audio/transcriptions`
- `services/api/app/repo/b2_transcripts.py` — `put_transcript`, `get_transcript`, `head_transcript_status_parallel`, `put_failed_marker`, `delete_transcript`
- `services/api/app/types/transcripts.py` — `Transcript`, `TranscriptSegment`

## Canonical Files
- Service entrypoint: `services/api/app/service/transcription.py::transcribe_memo`
- Background-task wrapper: `services/api/app/service/transcription.py::run`

## Inputs
- `memo_key`: canonical `audio/<YYYY>/<MM>/<stem>.<ext>` key

## Outputs
- On success: `transcripts/<YYYY>/<MM>/<stem>.json` containing `Transcript` (text, segments with `start`/`end`/`text`, `language`, `model`, `generated_at`)
- On failure: `transcripts/.failed/<YYYY>/<MM>/<stem>.json` with `{memo_key, error, failed_at}`
- Side effects: fans out to `service.tagging.run(key)` and `service.related_memos.run(key)` on success

## Flow
1. `runtime/upload.py` enqueues `transcription.run(key)` via `BackgroundTasks` after the audio object is written.
2. `transcription.run` calls `transcribe_memo`:
   - Validates the key.
   - HEADs the audio object; aborts with `FileNotFoundError` if missing.
   - Streams the audio bytes via the existing `get_s3_client`.
   - Calls `repo/transcription_client.transcribe` (Whisper `verbose_json`).
   - Persists the structured `Transcript` to B2.
3. On success, fans out to tagging + embedding stages.
4. On `TranscriptionClientError`, writes the `.failed/` marker so the UI status flips to `failed`.

## Edge Cases
- `OPENAI_API_KEY` missing -> client raises `TranscriptionClientError`; `.failed/` marker written.
- Audio > Whisper limit (25 MB) -> Whisper returns 4xx; same `.failed/` path.
- B2 GET for audio fails -> exception is swallowed by the background-task wrapper and logged; user can re-queue.

## Verification
- Manual: upload a short WAV/MP3, watch `transcripts/` populate.
- Programmatic: `test_httpx_only_in_repo` ensures production `httpx` imports stay in `app/repo/`.
- Quick verify command: `pnpm check:structure && pnpm lint:api`

## Related Docs
- [Tagging](tagging.md)
- [Cross-references](cross-references.md)
- [Memo capture](memo-capture.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

<!-- last_verified: 2026-05-26 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with memo-centric stats (total memos, total minutes, transcribed vs pending), recent memo activity, memo formats breakdown
  - **Memos** (`/memos`) — `MemoCard` grid scoped to the `audio/` prefix; status badges, tag chips, transcript previews
  - **Memo detail** (`/memos/[...key]`) — full transcript with timestamp anchors, tag/topic/entity chips, related memos (top-5 by cosine), audio player, delete cascade
  - **Record** (`/record`) — in-browser MediaRecorder UI with a Web Audio level meter; POSTs to `/memos`
  - **Upload** (`/upload`) — drag-and-drop with progress tracking; audio uploads land under `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>`
  - **Summary** (`/summary`) — daily / weekly AI rollups; "Generate" if not cached
  - **Files** (`/files`) — full B2 bucket explorer (tree view, preview, download, delete) for ops-style browsing
  - Dark mode via `next-themes`; PWA manifest + service-worker stub
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for memos, transcripts, tags, embeddings, summaries, upload, files
  - B2 S3 integration via boto3 with `user_agent_extra=b2ai-voice-memo-ai-second-brain`
  - OpenAI pipeline (Whisper / chat / embeddings) wrapped in three small `repo/*_client.py` adapters
  - Pipeline orchestration via FastAPI `BackgroundTasks` (no separate worker)
  - Audio metadata extraction (`.wav` via stdlib `wave`, everything else via `mutagen` — no ffmpeg)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API (`FileMetadata`, `Memo`, `Transcript`, `MemoTags`, `RelatedMemo`, `Summary`, `UploadStats`, …)
  - Consumed by `apps/web/` as workspace dependency

## Pipeline

```
record / upload              background tasks (FastAPI BackgroundTasks)
 ┌─────────────────┐
 │ POST /upload    │ ────────▶ audio/<YYYY>/<MM>/<stem>.<ext>
 │ POST /memos     │              │
 └─────────────────┘              │ enqueue
                                  ▼
                          service.transcription.run(key)
                                  │
                       OK ────────┼──────── fail
                       │                     │
            transcripts/<stem>.json    transcripts/.failed/<stem>.json
                       │
                       ├──▶ service.tagging.run(key)   ──▶ tags/<stem>.json
                       │
                       └──▶ service.related_memos.run  ──▶ embeddings/<stem>.json

On demand:
  POST /summaries/generate { window=daily|weekly, period }
  └──▶ service.summaries.generate_summary
        loads transcripts in window -> OpenAI chat -> summaries/<YYYY>/<DD>.md
```

`BackgroundTasks` is FastAPI's stdlib orchestrator — it runs after the response is returned, on the same process. For v1 this is sufficient (one user, in-memory queue). The transcription, tagging, embedding, and summary services are stateless and idempotent, so promoting to RQ / Celery / Cloud Tasks later is a route-handler change only.

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client + OpenAI HTTP wrappers) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer (verified by `test_boto3_only_in_repo`)
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, Memo, Transcript, MemoTags, …)
    config/                Settings loaded from environment (B2_* + OPENAI_*)
    repo/                  B2 + OpenAI clients (b2_client, b2_audio, b2_transcripts, b2_tags,
                          b2_embeddings, b2_summaries, transcription_client, llm_client,
                          embeddings_client)
    service/               Business logic — memos, transcription, tagging, related_memos,
                          summaries, files, upload, audio_metadata
    runtime/               FastAPI handlers — health, upload, memos, transcription, tagging,
                          summaries, files, metrics
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` and `httpx` (when used against external APIs) are only imported in `app/repo/`. All other layers interact through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No mutable globals**: Configuration is read-only after init. No module-level mutable state shared between layers.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. Memo keys validated against `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus|webm)$` (case-insensitive) with explicit `..` / `//` rejection before any B2 call. The pattern accepts both the Upload pipeline's canonical `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>` shape and externally-seeded audio.
- **Custom user agent**: every `boto3.client("s3", …)` sets `Config(user_agent_extra="b2ai-voice-memo-ai-second-brain")`. No `b2-native` calls.
- **No DB**: pipeline status is derived from B2 object presence (`transcripts/<stem>.json` vs `transcripts/.failed/<stem>.json`). Tags / embeddings / summaries are JSON or markdown blobs.

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repo
  - See `infra/railway/README.md` for configuration

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API)
  - `audio/` — raw memos (the Memos list scopes to this prefix)
  - `uploads/` — non-audio uploads (only show in Files)
  - `transcripts/` (+ `transcripts/.failed/`) — Whisper output
  - `tags/` — LLM tag/topic/entity JSON
  - `embeddings/` — embedding vectors
  - `summaries/` — daily/weekly markdown + JSON sidecars
  - File listing and metadata via S3 `list_objects_v2` / `head_object`
  - **No application database** — B2 is the sole data store

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, deletion, presigned URLs
- **OpenAI API** — Whisper (transcription), gpt-4o-mini (tags + summaries), text-embedding-3-small (cross-references); all three are configurable

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins
- **API -> B2** — authenticated via application keys, signature v4
- **API -> OpenAI** — `OPENAI_API_KEY` lives in server-side env; never shipped to the browser
- **Client -> B2** — presigned URLs for playback (inline) and download (attachment); 10-min expiry

## Data Flows

- **Memo upload**: Browser -> `POST /upload` (multipart) -> API validates -> service orchestrates -> repo writes to B2 at `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>` -> audio metadata extracted -> `BackgroundTasks` enqueues `transcription.run`
- **Transcription**: BackgroundTask -> repo fetches audio -> `repo/transcription_client.transcribe` -> `repo/b2_transcripts.put_transcript` -> fans out to tagging + embedding tasks
- **Memos list**: Browser -> `GET /memos` -> `service.memos.list_memos` lists `audio/`, HEADs sibling transcripts in parallel, and returns `Memo[]` with `transcription_status` + `tags`
- **Memo detail**: Browser -> `GET /memos/<key>/transcript` + `/tags` + `/related` (three parallel TanStack queries) -> service reads B2 -> JSON returned
- **Related memos**: `service.related_memos.find_related` loads every `embeddings/*.json` into memory, runs cosine, returns top-K
- **Summary generate**: Browser -> `POST /summaries/generate` -> `service.summaries.generate_summary` aggregates in-window transcripts -> OpenAI chat -> writes `summaries/<period>.md` + JSON sidecar
- **Delete cascade**: Browser -> `DELETE /memos/<key>` -> `service.memos.delete_memo` removes audio + transcript + tags + embedding from B2 -> TanStack invalidates

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## Canonical Files

- Memo route handlers: `services/api/app/runtime/memos.py`
- Memo service orchestration: `services/api/app/service/memos.py`
- Transcription pipeline: `services/api/app/service/transcription.py` (calls `repo/transcription_client.py`)
- Tagging pipeline: `services/api/app/service/tagging.py` (calls `repo/llm_client.py`)
- Cross-references: `services/api/app/service/related_memos.py` (calls `repo/embeddings_client.py`)
- Summaries: `services/api/app/service/summaries.py`
- B2 data access: `services/api/app/repo/b2_client.py` (UA-pinned), `b2_audio.py`, `b2_transcripts.py`, `b2_tags.py`, `b2_embeddings.py`, `b2_summaries.py`
- Audio metadata extractor: `services/api/app/service/audio_metadata.py`
- Pydantic models: `services/api/app/types/` (`files.py`, `memos.py`, `transcripts.py`, `tags.py`, `summaries.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config: `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Memo UI: `apps/web/src/components/memos/{memo-card,memos-view,memo-detail,transcript-view,related-memos,tag-chip,memo-status-badge,waveform}.tsx`
- Recorder: `apps/web/src/components/record/{recorder,level-meter}.tsx`
- Summary UI: `apps/web/src/components/summary/summary-view.tsx`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Memo capture](docs/features/memo-capture.md)
- [Memo library](docs/features/memo-library.md)
- [Memo playback](docs/features/memo-playback.md)
- [Memo metadata extraction](docs/features/memo-metadata.md)
- [Transcription](docs/features/transcription.md)
- [Tagging](docs/features/tagging.md)
- [Cross-references](docs/features/cross-references.md)
- [Summaries](docs/features/summaries.md)
- [Mobile / PWA](docs/features/mobile-pwa.md)
- [Bucket explorer](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions

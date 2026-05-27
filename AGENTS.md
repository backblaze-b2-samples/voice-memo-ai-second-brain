# AGENTS.md

This is the authoritative control surface for all coding agents on the
**Voice Memo AI Second Brain**. Read this first.

## 1. Repository Map

```
apps/web/                                  Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  src/app/memos/                           /memos — voice-memo grid (sample-specific)
  src/app/memos/[...key]/                  /memos/<key> — memo detail (transcript + tags + related)
  src/app/record/                          /record — in-browser MediaRecorder
  src/app/upload/                          /upload — drag-and-drop upload
  src/app/summary/                         /summary — daily/weekly AI rollups
  src/app/files/                           /files  — full-bucket explorer (kept from starter)
  src/components/memos/                    memo-card, memos-view, memo-detail, waveform,
                                           transcript-view, related-memos, tag-chip,
                                           memo-status-badge
  src/components/record/                   recorder, level-meter
  src/components/summary/                  summary-view
  public/manifest.webmanifest              PWA manifest (links from app/layout.tsx)
  public/sw.js                             Service-worker stub (no caching)
services/api/                              FastAPI backend (layered: types/config/repo/service/runtime)
  app/runtime/memos.py                     /memos, /memos/<key>/{playback|download|transcript|tags|related}
  app/runtime/transcription.py             POST /memos/<key>/transcribe (re-queue)
  app/runtime/tagging.py                   POST /memos/<key>/retag (re-queue)
  app/runtime/summaries.py                 /summaries, /summaries/generate
  app/runtime/upload.py                    /upload + /memos POST — fans out to transcription
  app/service/memos.py                     memo key validation, list/head/delete + sibling cascade
  app/service/transcription.py             Whisper orchestration + .failed/ markers
  app/service/tagging.py                   LLM tag/topic/entity extraction
  app/service/related_memos.py             embeddings + in-process cosine top-K
  app/service/summaries.py                 daily/weekly markdown rollups
  app/service/audio_metadata.py            wave + mutagen extractor
  app/repo/b2_client.py                    boto3 — generic file helpers + UA pinning
  app/repo/b2_audio.py                     audio-prefix helpers, head_audio_objects_parallel
  app/repo/b2_transcripts.py               transcripts/ read/write/status
  app/repo/b2_tags.py                      tags/ read/write
  app/repo/b2_embeddings.py                embeddings/ read/write + cosine inputs
  app/repo/b2_summaries.py                 summaries/ markdown + JSON sidecar
  app/repo/transcription_client.py         OpenAI Whisper HTTP wrapper (httpx)
  app/repo/llm_client.py                   OpenAI chat HTTP wrapper (httpx)
  app/repo/embeddings_client.py            OpenAI embeddings HTTP wrapper (httpx)
  app/types/memos.py                       Memo (was AudioAsset)
  app/types/transcripts.py                 Transcript + TranscriptSegment
  app/types/tags.py                        MemoTags + RelatedMemo
  app/types/summaries.py                   Summary + SummaryListEntry
packages/shared/                           Shared TypeScript types (Memo, Transcript, MemoTags, …)
docs/                                      System of record (features, workflows, security, reliability)
docs/exec-plans/                           Execution plans and tech debt tracker
infra/railway/                             Deployment config
```

## 2. Architectural Invariants

**Backend layering**: `types` -> `config` -> `repo` -> `service` -> `runtime`

- No backward imports across layers
- No `boto3` (or `httpx` to external APIs) outside `repo/`
- No business logic in route handlers (`runtime/`)
- All external APIs wrapped in `repo/` adapters
- All request/response data validated at boundary (Pydantic models)
- No shared mutable state across layers

**Frontend**: shadcn/ui components in `src/components/ui/` are generated — never modify them.

**Data fetching**: every API call flows through TanStack Query hooks in `apps/web/src/lib/queries.ts`. No bare `useEffect + fetch` patterns. New endpoints touch three files: `runtime/<router>.py`, `lib/api-client.ts`, `lib/queries.ts`.

**B2 prefixes (all derived from one bucket, no DB):**

| Prefix | What lives there | Owner module |
|---|---|---|
| `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>` | Raw memos uploaded via `/upload` or `/record` | `runtime/upload.py` |
| `uploads/<safe>` | Non-audio uploads (kept for parity with the bucket explorer) | `runtime/upload.py` |
| `transcripts/<YYYY>/<MM>/<stem>.json` | Whisper output | `service/transcription.py` |
| `transcripts/.failed/<YYYY>/<MM>/<stem>.json` | Markers for transcription failures | `service/transcription.py` |
| `tags/<YYYY>/<MM>/<stem>.json` | LLM-extracted tags / topics / entities | `service/tagging.py` |
| `embeddings/<YYYY>/<MM>/<stem>.json` | Embedding vectors for cross-references | `service/related_memos.py` |
| `summaries/<YYYY>/<DD>.md` + sidecar `.json` | Daily AI rollups | `service/summaries.py` |
| `summaries/<YYYY>/W<WW>.md` + sidecar `.json` | Weekly AI rollups | `service/summaries.py` |

Memo keys are produced by the Upload pipeline at `audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>` — the `--<uuid>` suffix keeps keys collision-proof while leading with the filename keeps keys scannable. Externally-seeded audio (B2 console, prior sample, direct sync) without a `--` suffix is still listed and playable. Path-traversal payloads (`..`, `//`) are rejected at the API boundary by `service/memos.py::MEMO_KEY_RE`.

**Pipeline status (no DB) **: the `/memos` endpoint derives `transcription_status` per memo by HEAD-checking `transcripts/<stem>.json` and `transcripts/.failed/<stem>.json` in parallel via `repo/b2_transcripts.head_transcript_status_parallel`. Same pattern is used by the dashboard aggregates.

**Pipeline trigger**: `runtime/upload.py` enqueues `service.transcription.run(key)` via FastAPI `BackgroundTasks` after a successful audio upload. The transcription service then fans out to `service.tagging.run` and `service.related_memos.run` on success. Failures write a `.failed/` marker — no DB rows to invalidate.

**Delete cascade**: `service/memos.py::delete_memo` removes the audio object AND every sibling artifact (`transcripts/`, `tags/`, `embeddings/`) keyed off the memo's stem. `bulk_delete_memos` does the same for batches.

**B2 surface**: S3-only. No `b2-native` calls anywhere. Every `boto3.client("s3", …)` instantiation MUST pass `Config(user_agent_extra="b2ai-voice-memo-ai-second-brain")`. No hardcoded region strings in source (use `B2_REGION` from `.env`).

## 3. Quality Expectations

- **DRY** — do not duplicate logic, types, or constants. Extract shared code only when used in 2+ places.
- Structured JSON logging only — no `print()` statements
- No raw SDK calls outside `repo/` layer
- Files stay under 300 lines
- Tests added or updated for every behavior change
- Docs updated in same PR as code changes
- Lint clean before merge
- Prefer boring, composable libraries over clever abstractions
- No implicit type assumptions — use typed models

## 4. Mechanical Enforcement

| Rule | Enforced by |
|------|-------------|
| No backward imports | `tests/test_structure.py::test_no_backward_imports` |
| No boto3 outside repo/ | `tests/test_structure.py::test_boto3_only_in_repo` |
| File size < 300 lines | `tests/test_structure.py::test_file_size_limits` |
| All layers exist | `tests/test_structure.py::test_all_layers_exist` |
| No bare print() | `ruff` rule T20 |
| Import ordering | `ruff` rule I001 |
| Frontend strict equality | `eslint` rule eqeqeq |
| No unused vars | `eslint` + `ruff` rules |

## 5. Commands

```bash
# Run
pnpm dev               # start both frontend and backend
pnpm dev:web           # frontend only
pnpm dev:api           # backend only

# Test & Lint
pnpm lint              # frontend lint (eslint)
pnpm build             # frontend type check + build
pnpm lint:api          # backend lint (ruff)
pnpm test:api          # backend tests (pytest)
pnpm check:structure   # structural boundary tests
pnpm test:e2e          # Playwright e2e tests
```

## 6. Agent Workflow

1. Read this file first.
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) before structural changes.
3. For non-trivial changes, create a plan in `docs/exec-plans/active/`.
4. Implement the smallest coherent change.
5. Run: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
6. Update docs in the same PR (see §8).
7. Move completed plans to `docs/exec-plans/completed/`.
8. Only change files relevant to the task. No drive-by improvements.

## 7. Frontend Conventions

See [docs/dev-workflows.md](docs/dev-workflows.md) for full details.

## 8. Doc Update Mapping

| Change Type | Update Location |
|-------------|-----------------|
| Feature logic, inputs, outputs, tests | `docs/features/<feature>.md` |
| User journeys | `docs/app-workflows.md` |
| System layout, deployments | `ARCHITECTURE.md` |
| Dev or testing process | `docs/dev-workflows.md` |
| Setup or scope changes | `README.md` |
| Security changes | `docs/SECURITY.md` |
| Reliability changes | `docs/RELIABILITY.md` |
| Active work plans | `docs/exec-plans/active/` |
| Known tech debt | `docs/exec-plans/tech-debt-tracker.md` |

If documentation and implementation conflict, update docs in the same PR. Documentation rot destroys agent reliability.

## 9. Doc Map

| Topic | Location |
|-------|----------|
| System layout, data flows, boundaries | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Feature docs | [docs/features/](docs/features/) |
| User journeys | [docs/app-workflows.md](docs/app-workflows.md) |
| Engineering workflows and testing | [docs/dev-workflows.md](docs/dev-workflows.md) |
| Security principles | [docs/SECURITY.md](docs/SECURITY.md) |
| Reliability expectations | [docs/RELIABILITY.md](docs/RELIABILITY.md) |
| Execution plans | [docs/exec-plans/](docs/exec-plans/) |
| Tech debt | [docs/exec-plans/tech-debt-tracker.md](docs/exec-plans/tech-debt-tracker.md) |

## 10. When Unsure

- Prefer boring, stable libraries (stdlib `wave`, `mutagen`, `httpx` — no ffmpeg, no async OpenAI SDK)
- Prefer small PRs over large changes
- Add tests with every change
- Never bypass lint rules without explicit instruction
- Ask before making destructive or irreversible changes

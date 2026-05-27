# Plan: `voice-memo-ai-second-brain`

> **Source override (read first):** Per the user's invocation, the source of
> truth for this scaffold is **`ai-audio-starter-kit`** (cloned fresh into
> `.claude/scratch/vcsk-e4f7c2af-e8c1-4335-8928-c389f5f3a8b5/`), **not**
> `vibe-coding-starter-kit`. Every reference to "the starter kit" or "the
> source tree" below means the audio starter kit at that scratch path.
> The builder agent's hardcoded step that would re-clone
> `vibe-coding-starter-kit` MUST be skipped — the Phase 2 prompt instructs
> it to copy from the scratch path instead.

## 1. Purpose

`voice-memo-ai-second-brain` is a Backblaze B2 sample app that turns spoken
voice memos into a searchable, summarized personal knowledge base.
A user records short memos from their phone (PWA + in-browser recorder, or
drag-and-drop upload), the raw audio lands in B2, and an automatic pipeline
transcribes it (Whisper), extracts tags, computes an embedding for
cross-reference, and rolls up daily/weekly AI summaries — every derived
artifact (transcript JSON, tags JSON, embedding vector, markdown summary)
is also stored in B2 under its own prefix. This makes B2 the *only*
persistence layer: there is no database. Audio data is naturally heavy and
accumulates indefinitely, exactly the storage curve B2 is priced for. The
sample targets developers exploring "AI second brain" / "voice journal"
patterns who want a concrete reference for layered B2-as-data-store
architecture across raw + derived artifacts.

## 2. Architecture delta from `ai-audio-starter-kit`

The starter kit is already most of this app. We keep the entire backbone
and add four pipeline stages (transcribe → tag → embed → summarize) plus
a memo-detail UI and a PWA recorder.

| Keep (as-is or cosmetic rename) | Trim / rewrite | Add (new for this sample) |
|---|---|---|
| Monorepo layout (`apps/web` Next.js 16, `services/api` FastAPI, `packages/shared` TS types) | Audio-generic framing in README / AGENTS / ARCHITECTURE → reframed as voice-memo second brain | **/memos page** — sample-scoped (replaces `/library`, same B2 prefix `audio/`, card surfaces transcript preview + tag chips + "Transcribing…" status) |
| Layered backend invariants: `types → config → repo → service → runtime`, structural tests, 300-line cap, no `boto3` outside `repo/` | `apps/web/src/app/library/` → renamed to `apps/web/src/app/memos/` (URL & directory); existing `library` queries/types are reshaped | **/memos/[key] detail page** — full transcript w/ timestamp anchors, tag chips, "Related memos" section (top-5 by cosine), audio player, delete |
| **`/files` full-bucket explorer (NON-NEGOTIABLE KEEP)** — `apps/web/src/app/files/` and `components/files/` unchanged in structure | Dashboard `format-breakdown.tsx` — keep file, reframe label "Memo formats" (most memos will be one format, but the component is generic) | **/record page** — MediaRecorder + canvas-based level meter; POSTs to `/memos` (same upload endpoint, just an alternative client) |
| `/upload` drag-and-drop + audio metadata extraction (wave + mutagen) | `audio-library.md`, `audio-playback.md`, `audio-metadata.md` feature docs → rewritten to `memo-library.md`, `memo-playback.md`, `memo-metadata.md` | **/summary page** — daily/weekly AI-generated summary view; "Generate" button if not yet cached |
| `/design` design system showcase + Audio Library Card primitive (kept; component renamed `memo-card.tsx` and re-themed) | `dashboard.md` feature doc → rewritten for memo-centric metrics | **Transcription pipeline** — `repo/transcription_client.py` (OpenAI Whisper HTTP), `repo/b2_transcripts.py`, `service/transcription.py`, `runtime/transcription.py` |
| Audio key convention `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>` and `service/library.py::AUDIO_KEY_RE` validator | `file-upload.md` → rewritten to `memo-capture.md` covering both drag-drop and the new PWA recorder | **Tagging pipeline** — `repo/llm_client.py` (shared OpenAI chat), `repo/b2_tags.py`, `service/tagging.py`, `runtime/tagging.py` |
| TanStack Query data layer; `lib/queries.ts`, `lib/api-client.ts` shape | Audio Library Card → `memo-card.tsx` (adds transcript-preview line + tag-chip row + status badge) | **Embeddings + cross-refs** — `repo/embeddings_client.py` (OpenAI embeddings), `repo/b2_embeddings.py`, `service/related_memos.py`, `GET /memos/{key}/related` |
| B2 S3 client w/ `Config(user_agent_extra=...)` pattern; `B2_*` env var names | Stats cards on dashboard (rename labels: "Total memos", "Total minutes", "Transcribed", "Pending") — same `runtime/library.py` aggregates extended w/ transcript-presence count | **Summaries** — `service/summaries.py` aggregates transcripts within a date window, writes markdown to `summaries/<YYYY>/<DD>.md` or `summaries/<YYYY>/W<WW>.md`; `GET /summaries`, `POST /summaries/generate` |
| Dark mode (`next-themes`), pre-commit hooks, doctor script, structural tests, JSON logging, `/metrics` endpoint | `Audio` namespace in shared types → `Memo` namespace (e.g., `AudioAsset` → `Memo` with optional `transcript`, `tags`, `embedding_present` fields) | **PWA manifest + service worker stub** — `apps/web/public/manifest.webmanifest`, `next.config.ts` PWA config, icons (use simple text-only SVGs scaffolded by the builder; no binary art) |
| Playwright e2e harness (extend with new pages) | — | **B2 prefixes** added to bucket convention: `transcripts/`, `tags/`, `embeddings/`, `summaries/` (alongside existing `audio/` and `uploads/`) |
| Health endpoint w/ B2 connectivity check | — | **Pipeline trigger** — `runtime/upload.py` after-write hook spawns `BackgroundTasks` running `service/transcription.run(key)` → on success spawns tagging + embedding tasks; on failure writes `transcripts/.failed/<key>.json` (no extra worker process for v1) |

### Bucket explorer policy (explicit, per skill non-negotiable)

- **Keep**: `/files` route, `components/files/`, `runtime/files.py`,
  `service/files.py`, repo helpers — unchanged in structure (only string
  renames). This is the full-bucket explorer the skill mandates.
- **Add (sample-scoped)**: `/memos` (the renamed `/library`) — scoped to
  the `audio/` prefix only, surfaces memo-specific UI (transcript preview,
  tags, status). The detail page `/memos/[key]` is also sample-scoped.

### Non-goals (explicit out of scope for v1)

- No vector database / FAISS index — naïve cosine over JSON-stored
  embeddings is sufficient for thousands of memos; documented as a v2
  upgrade in `docs/features/cross-references.md`.
- No scheduler / cron — summaries are user-triggered with B2-as-cache;
  documented as a v2 upgrade.
- No standalone /search page — text-query search is a v2 extension of the
  related-memos endpoint.
- No iOS Shortcut bundled in the repo — the `POST /memos` contract is
  documented in `docs/features/memo-capture.md` so a user can build one,
  but no shortcut .json/.shortcut artifact is shipped (skill forbids
  binary asset creation without confirmation).

## 3. B2 surface (S3 API only — no `b2-native`)

| Operation | Used by | Notes |
|---|---|---|
| `PutObject` | Upload (audio), Transcription (writes JSON), Tagging (writes JSON), Embeddings (writes JSON), Summaries (writes md) | All derived artifacts written by the API after successful generation. |
| `GetObject` | Transcript retrieval, tag retrieval, summary retrieval, embedding load | `repo/b2_transcripts.py::get_transcript` etc. |
| `HeadObject` | Memo status (does `transcripts/<key>.json` exist?), file-browser metadata | Reuses existing `head_audio_objects_parallel` pattern for batch status. |
| `ListObjectsV2` | Memo list (audio/ prefix), files explorer (everything), summaries listing (summaries/ prefix) | Existing helpers reused; new prefix listers added in `repo/b2_transcripts.py`, `b2_summaries.py`. |
| `DeleteObject` / `DeleteObjects` | Memo delete (must also remove transcript / tags / embedding / from summaries cache invalidation) | `service/library.py::delete_memo` extended to delete the four sibling artifacts. |
| Presigned URL (`generate_presigned_url`) | Audio playback (inline), download (attachment) | Existing `presign_audio_playback` pattern reused. |

**No `b2-native` usage anywhere.** Every `boto3.client("s3", …)`
instantiation MUST pass `Config(user_agent_extra="b2ai-voice-memo-ai-second-brain")`.

## 4. Key features

1. **Frictionless capture** — PWA-installable web app with an in-browser MediaRecorder UI at `/record`, plus the existing drag-and-drop `/upload`. Both write to `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>` in B2.
2. **Automatic transcription** — OpenAI Whisper API turns each new memo into a transcript JSON written to `transcripts/<YYYY>/<MM>/<key-stem>.json` in B2. Triggered by FastAPI `BackgroundTasks` after upload.
3. **AI tags & keywords** — After transcription, an OpenAI chat call extracts tags / topics / entities into `tags/<YYYY>/<MM>/<key-stem>.json`. Surfaced as chips on the memo card and detail page.
4. **Cross-reference search** — OpenAI embeddings stored as JSON in `embeddings/<YYYY>/<MM>/<key-stem>.json`; `GET /memos/{key}/related` ranks by cosine similarity in-process and returns top-5 related memos.
5. **Daily / weekly AI summaries** — On user demand, the API aggregates transcripts in a date window, sends them to OpenAI chat, and writes markdown to `summaries/<YYYY>/<DD>.md` (daily) or `summaries/<YYYY>/W<WW>.md` (weekly). Re-requests return the cached B2 object.
6. **Full B2 bucket explorer (kept from starter)** — `/files` tree view, preview, download, delete for ops-style browsing across `audio/`, `transcripts/`, `tags/`, `embeddings/`, `summaries/`, and any other key.

## 5. Doc transforms

### Rewritten (same path, new content)
- `README.md` — keep skeleton (badges, Quick Start, env table) but reframe top section as voice-memo second brain; add `OPENAI_API_KEY` to env table; new "What it looks like" section references `/memos`, `/record`, `/summary`.
- `AGENTS.md` — update name and one-line description; extend repo map with new routes, new repo helpers, new B2 prefixes; extend "Audio storage convention" section with `transcripts/`, `tags/`, `embeddings/`, `summaries/` conventions; update `user_agent_extra` value.
- `ARCHITECTURE.md` — add a "Pipeline" subsection with the diagram `Capture → Transcribe → Tag → Embed (→ Summarize on demand)`; note `BackgroundTasks` as the v1 orchestrator and the "no DB; status derived from object presence" invariant.
- `docs/app-workflows.md` — rewrite user journeys around voice memos (record-on-phone, daily-review, weekly-rollup).
- `docs/dev-workflows.md` — keep structure; add LLM-key setup, note Whisper/OpenAI rate limits, add "How to swap providers" subsection pointing at `repo/transcription_client.py`, `repo/llm_client.py`, `repo/embeddings_client.py`.
- `docs/features/dashboard.md` — reframe metrics (memos / minutes / transcribed / pending) and recent activity (recent memos with tag chips).
- `docs/features/file-upload.md` → renamed to `docs/features/memo-capture.md` — covers `/upload`, `/record`, and the documented `POST /memos` API contract for iOS Shortcuts.
- `docs/features/audio-library.md` → renamed to `docs/features/memo-library.md` — `/memos` page, the renamed card primitive, status badges.
- `docs/features/audio-playback.md` → renamed to `docs/features/memo-playback.md`.
- `docs/features/audio-metadata.md` → renamed to `docs/features/memo-metadata.md` — same wave/mutagen extractor; framing only.
- `docs/features/file-browser.md` — keep largely unchanged (full-bucket explorer); update preface to clarify new bucket prefixes are visible.
- `docs/features/_template.md` — unchanged.

### Newly stubbed
- `docs/features/transcription.md`
- `docs/features/tagging.md`
- `docs/features/cross-references.md`
- `docs/features/summaries.md`
- `docs/features/mobile-pwa.md` — installation, MediaRecorder browser support matrix, recording UX.

### Deleted
- None — the starter kit's docs all map cleanly to renamed/rewritten counterparts; nothing is dead weight.

### Exec plan
- This file (after build completes) becomes
  `./voice-memo-ai-second-brain/docs/exec-plans/completed/initial-scaffold.md`.

## 6. Rename table

The builder applies these globally (skip `node_modules`, `.venv`, `dist`,
`build`, `.next`, `pnpm-lock.yaml`).

| From (in `ai-audio-starter-kit`) | To (in `voice-memo-ai-second-brain`) | Where it appears |
|---|---|---|
| `ai-audio-starter-kit` | `voice-memo-ai-second-brain` | `package.json` name, `pnpm-workspace` filters, README badges, repo URLs, `utm_content`, image tags, workflow slugs, docs cross-links |
| `ai_audio_starter_kit` | `voice_memo_ai_second_brain` | Python module / fixture names if present, Docker image labels |
| `AI Audio Starter Kit` | `Voice Memo AI Second Brain` | README H1, AGENTS H1, ARCHITECTURE H1, `<title>` in Next layout |
| `@ai-audio-starter-kit/web` | `@voice-memo-ai-second-brain/web` | Workspace package name, `pnpm --filter` invocations |
| `@ai-audio-starter-kit/shared` | `@voice-memo-ai-second-brain/shared` | Shared package, if scoped |
| `b2ai-ai-audio-starter-kit` | `b2ai-voice-memo-ai-second-brain` | `Config(user_agent_extra=...)` literal in every boto3 client; UTM tag on Backblaze links |
| `Audio Library` (UI strings) | `Memos` | Sidebar nav, page titles, button labels |
| `Audio Asset Card` / `AudioAssetCard` | `Memo Card` / `MemoCard` | Component file, story, design page reference |
| `audio-asset-card.tsx` | `memo-card.tsx` | File rename + import updates |
| `library-view.tsx` | `memos-view.tsx` | File rename + import updates |
| `audio-library.md`, `audio-playback.md`, `audio-metadata.md`, `file-upload.md` | `memo-library.md`, `memo-playback.md`, `memo-metadata.md`, `memo-capture.md` | `docs/features/` |
| `/library` (route) | `/memos` | `apps/web/src/app/library/` directory rename; nav link; e2e test selectors |
| `useLibrary`, `useDeleteAudioAsset`, `useBulkDeleteAudioAssets` | `useMemos`, `useDeleteMemo`, `useBulkDeleteMemos` | `lib/queries.ts`, `lib/api-client.ts` |
| `AudioAsset` (TS + Pydantic) | `Memo` | `packages/shared/src/types.ts`, `services/api/app/types/library.py` (rename file to `memos.py`) |
| `audio-aware`, `audio-centric`, `audio-first` (marketing copy) | `memo-aware`, `memo-centric`, `memo-first` | README, ARCHITECTURE, AGENTS, feature docs |
| `Build AI audio applications…` (README hook) | `Build a personal voice-memo second brain…` | README |

> **Reviewer note (for Phase 3):** The standard reviewer checks for
> leftover `vibe-coding-starter-kit` strings. For this sample, the
> equivalent check is for leftover **`ai-audio-starter-kit`**,
> **`ai_audio_starter_kit`**, **`AI Audio Starter Kit`** strings. Any
> occurrence outside an explicit "Derived from `ai-audio-starter-kit`"
> historical-note context is ❌.

## 7. Open questions resolved

- **Transcription provider** → OpenAI Whisper API (single `OPENAI_API_KEY` env var also powers tagging + embeddings; `repo/*_client.py` boundary keeps swaps cheap).
- **Mobile capture** → PWA + in-browser recorder at `/record`; `POST /memos` endpoint documented in `docs/features/memo-capture.md` for future iOS Shortcuts / Android Tasker integration.
- **Cross-references** → embeddings JSON in B2 + naïve in-process cosine; v2 upgrade to a vector index documented.

## 8. New env vars

Added to `.env.example` (in addition to the existing `B2_*` keys, which are
unchanged):

```
# OpenAI (required) — drives Whisper transcription, tag/keyword extraction,
# embeddings for cross-references, and AI summary generation.
OPENAI_API_KEY=your_openai_api_key

# Optional model overrides (defaults shown)
# OPENAI_TRANSCRIPTION_MODEL=whisper-1
# OPENAI_CHAT_MODEL=gpt-4o-mini
# OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## 9. Parent CLAUDE.md note

The agents reference `../CLAUDE.md` for parent repo standards.
`/Users/epavez/Documents/sampleapps/CLAUDE.md` does **not** currently
exist. The standards (S3-only default, custom `user_agent_extra`,
standardized `B2_*` env var names) are enforceable via the `b2-doctor`
skill and the explicit rules in this plan, so the build and review can
proceed without that file. The builder / reviewer should treat the
b2-doctor output as the standards check.

<!-- last_verified: 2026-05-26 -->
# Feature: Memo Library

## Purpose
List every voice memo the user has stored in B2, annotated with pipeline status, tag chips, and a transcript preview — sourced entirely from S3 list/head and the sibling artifact prefixes (`transcripts/`, `tags/`). Scoped to the `audio/` prefix; the full bucket lives at `/files`.

## Used By
- UI: `/memos` (grid) and `/memos/[...key]` (detail)
- API:
  - `GET /memos`
  - `GET /memos/{key}/playback`
  - `GET /memos/{key}/download`
  - `GET /memos/{key}/transcript`
  - `GET /memos/{key}/tags`
  - `GET /memos/{key}/related`
  - `DELETE /memos/{key}`
  - `POST /memos/bulk-delete`

## Core Functions
- `apps/web/src/components/memos/memos-view.tsx` — responsive grid (`sm:grid-cols-2 xl:grid-cols-3`), Refresh, EmptyState, ErrorState, multi-select header + bulk-delete confirm
- `apps/web/src/components/memos/memo-card.tsx` — per-memo card: status badge, metadata strip, tag chips, transcript preview, Play / View / Download / Delete
- `apps/web/src/components/memos/memo-detail.tsx` — detail page composition: audio player, tag chips, transcript view, related memos, re-transcribe action
- `apps/web/src/components/memos/transcript-view.tsx` — segmented transcript with timestamp anchors
- `apps/web/src/components/memos/related-memos.tsx` — top-5 cosine-similarity card
- `apps/web/src/components/memos/{memo-status-badge,tag-chip,waveform}.tsx` — primitives
- `apps/web/src/lib/queries.ts::useMemos`, `useMemoTranscript`, `useMemoTags`, `useRelatedMemos`, `useDeleteMemo`, `useBulkDeleteMemos`, `useRetranscribeMemo`
- `apps/web/src/lib/api-client.ts::getMemos`, `getPlaybackUrl`, `getMemoDownloadUrl`, `getMemoTranscript`, `getMemoTags`, `getRelatedMemos`, `deleteMemo`, `bulkDeleteMemos`, `retranscribeMemo`
- `services/api/app/runtime/memos.py` — FastAPI routes
- `services/api/app/service/memos.py` — key validation, listing, delete (cascade), bulk delete, aggregates
- `services/api/app/repo/b2_audio.py`, `b2_transcripts.py`, `b2_tags.py`, `b2_embeddings.py`

## Canonical Files
- Pattern exemplar: `apps/web/src/components/memos/memo-card.tsx`
- Service orchestration: `services/api/app/service/memos.py`

## Inputs
- limit: int (query param on `GET /memos`, default 100, max 500)
- key: path param on `/memos/{key}/...` — must match `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus|webm)$` (case-insensitive) and contain no `..` or `//`. Canonical shape is `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>`.
- `POST /memos/bulk-delete` body: `{ keys: string[] }` (1-1000 keys)

## Outputs
- `GET /memos` -> `Memo[]` sorted newest-first. Each `Memo` carries `transcription_status` (one of `pending|transcribed|failed`) plus the tag array fetched in parallel from `tags/<stem>.json`.
- `GET /memos/{key}/playback` / `/download` -> `{ url, expires_in }`
- `GET /memos/{key}/transcript` -> `Transcript` or 404
- `GET /memos/{key}/tags` -> `MemoTags` (empty arrays when no tags yet)
- `GET /memos/{key}/related` -> `RelatedMemo[]` (top-5 by cosine; empty if embeddings missing)
- `DELETE /memos/{key}` -> `{ deleted: true, key }` + sibling artifacts removed
- `POST /memos/bulk-delete` -> `{ deleted, errors }`

## Flow
- `GET /memos` -> `list_objects_v2(Prefix="audio/")` -> sort newest-first -> three parallel fanouts (head metadata, transcript status HEAD, tags GET) -> assemble `Memo[]`.
- Pipeline status is derived: `transcripts/<stem>.json` -> `transcribed`; `transcripts/.failed/<stem>.json` -> `failed`; neither -> `pending`.
- Delete -> validate key -> `delete_object` for audio -> best-effort delete of `transcripts/`, `tags/`, `embeddings/` siblings.
- Bulk delete -> validate every key -> one `DeleteObjects` call -> per-key sibling cleanup.
- Detail page: three parallel TanStack queries (transcript, tags, related) plus a deferred audio playback fetch when the user hits "Load audio".

## Edge Cases
- Missing transcript -> `MemoStatusBadge` renders `Transcribing…`; `useMemoTranscript` polls automatically with 30s memo-list refetch
- Failed transcript -> badge flips to `Failed`; user can re-queue via `Re-transcribe`
- Externally-seeded audio (no `--<uuid>` suffix) -> still listed, played, deleteable. Tags/transcripts/embeddings will be missing until the pipeline runs (manual `POST /memos/{key}/transcribe`).
- Malformed key -> 400 from API before any B2 call
- Listed-but-not-head-able key -> 404 on playback/download

## UX States
- Loading: 6 skeleton cards
- Empty: "No memos yet — record one or upload an audio file"
- Loaded: responsive grid
- Error: `ErrorState` with Retry

## Verification
- Test files: `services/api/tests/test_bulk_delete.py` (memos half), `services/api/tests/test_audio_aggregates.py`, `services/api/tests/test_upload_conflict.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
- Pass criteria: pytest green, no ruff violations

## Related Docs
- [Memo capture](memo-capture.md)
- [Memo playback](memo-playback.md)
- [Memo metadata extraction](memo-metadata.md)
- [Transcription](transcription.md)
- [Tagging](tagging.md)
- [Cross-references](cross-references.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

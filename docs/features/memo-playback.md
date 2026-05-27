<!-- last_verified: 2026-05-26 -->
# Feature: Memo Playback

## Purpose
Play voice-memo audio directly from B2 in the browser without proxying bytes through the API. The card swaps its action row for a native `<audio controls>` element fed by a short-lived presigned URL.

## Used By
- UI: `apps/web/src/components/memos/memo-card.tsx`, `apps/web/src/components/memos/memo-detail.tsx`, `apps/web/src/components/dashboard/recent-uploads-table.tsx`
- API: `GET /memos/{key}/playback`, `GET /memos/{key}/download`

## Core Functions
- `services/api/app/runtime/memos.py` — `/memos/{key}/playback` and `/download` handlers
- `services/api/app/service/memos.py::get_playback_url`, `get_download_url`
- `services/api/app/repo/b2_audio.py::presign_audio_playback`
- `services/api/app/repo/b2_client.py::get_presigned_url`
- `apps/web/src/lib/api-client.ts::getPlaybackUrl`, `getMemoDownloadUrl`

## Canonical Files
- Presign pattern: `services/api/app/repo/b2_client.py`
- Playback UX: `apps/web/src/components/memos/memo-card.tsx`

## Inputs
- key: path param matching `^audio/[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(wav|mp3|flac|ogg|m4a|aac|opus|webm)$` (case-insensitive); `..` / `//` are rejected.

## Outputs
- `GET /memos/{key}/playback` -> `{ url: string, expires_in: 600 }` — presigned GET, no Content-Disposition (inline render)
- `GET /memos/{key}/download` -> `{ url: string, expires_in: 600 }` — presigned GET with `Content-Disposition: attachment; filename="..."`

## Flow
- User clicks **Play** on a `MemoCard` or the detail page
- Client calls `getPlaybackUrl(key)` -> `/memos/{key}/playback`
- Service validates the key, HEADs the object, mints a 10-minute presigned GET
- Browser plays the audio directly from B2 — the API is not in the playback path

## Expiry and caching
- 10-minute presigned URLs. Long enough to start playback, short enough that a stolen URL has limited blast radius.
- Each Play click mints a fresh URL; nothing is cached client-side.

## Edge Cases
- **Missing object** -> 404 ("Memo not found"); card toasts and stays pre-play
- **Malformed key** -> 400 before any B2 call
- **B2 unreachable** -> 500; card toasts

## UX States
- Pre-play: action row (Play / View / Download / Delete)
- Loading: Play button shows "Loading..."
- Playing: inline `<audio controls autoPlay>`
- Error: toast

## Verification
- Quick verify command: `pnpm test:api`
- Pass criteria: pytest green

## Related Docs
- [Memo library](memo-library.md)
- [Memo capture](memo-capture.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

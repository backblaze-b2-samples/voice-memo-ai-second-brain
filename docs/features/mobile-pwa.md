<!-- last_verified: 2026-05-26 -->
# Feature: Mobile / PWA

## Purpose
Install the app to a phone home screen and capture memos from a single tap. The sample ships a minimal manifest + service-worker stub — enough to satisfy the "Add to Home Screen" requirements without pretending to be offline-capable.

## Used By
- UI: `apps/web/src/app/layout.tsx` (registers the SW + links the manifest), `apps/web/src/app/record/page.tsx` (start_url target)
- Static assets: `apps/web/public/manifest.webmanifest`, `apps/web/public/sw.js`, `apps/web/public/icon.svg`

## Core Functions
- `apps/web/src/components/record/recorder.tsx` — MediaRecorder logic with codec fallback (`webm/opus` -> `mp4` -> `ogg/opus`)
- `apps/web/src/components/record/level-meter.tsx` — `AnalyserNode`-driven RMS meter on canvas

## Canonical Files
- Manifest: `apps/web/public/manifest.webmanifest`
- Service worker: `apps/web/public/sw.js`
- PWA glue: `apps/web/src/app/layout.tsx`

## Inputs / Outputs
- The user's microphone (gated by the browser's permission prompt)
- POSTs the recorded blob to `/memos` via `uploadMemo`

## Browser support matrix
- Chrome / Edge / Firefox / Safari ≥ 14 — MediaRecorder works; `webm/opus` everywhere except Safari (`mp4`)
- iOS Safari — installs as a PWA from "Add to Home Screen". MediaRecorder produces `audio/mp4` (m4a). Background recording is not supported by iOS Safari; closing the PWA stops the recording.
- Android Chrome — installs from the browser menu. `webm/opus`.

## Flow
1. `layout.tsx` declares `manifest: "/manifest.webmanifest"` + theme color.
2. The inline `register-sw` script registers `/sw.js`.
3. `sw.js` is intentionally pass-through — it doesn't cache anything. Caching memo transcripts or presigned URLs across users would be a privacy hazard; static-shell caching is the only reasonable extension for v2.
4. The manifest sets `start_url: "/record"` so the home-screen icon opens straight into the recorder.

## Edge Cases
- iOS PWA closes when backgrounded -> the recorder UI persists the blob in memory only; if the page is killed, the take is lost. We deliberately don't auto-upload partial blobs.
- Permission denied -> recorder toasts and stays in `idle`.
- Codec missing -> recorder falls back through the candidate list.

## Icons
The sample ships a single inline SVG icon (`/icon.svg`) referenced from the manifest. We deliberately avoid binary PNG icons in the repo — the SVG renders at any size, and the manifest's `purpose: "any"` covers most install surfaces. To support legacy iOS launchers that require a `180x180` PNG, generate one locally and add it to `manifest.webmanifest`.

## Verification
- Manual: `pnpm dev`, open in Chrome on a phone over the local network, hit the install prompt, open from home screen, record.
- Quick verify command: `pnpm build` (ensures the manifest + SW are emitted)

## Related Docs
- [Memo capture](memo-capture.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

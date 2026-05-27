<!-- last_verified: 2026-05-26 -->
# Feature: Memo Capture

## Purpose
Capture voice memos from three surfaces — the in-browser MediaRecorder UI at `/record`, the drag-and-drop uploader at `/upload`, and the documented `POST /memos` HTTP contract (for iOS Shortcuts / Android Tasker / programmatic capture). All three land at the same B2 prefix and kick off the same transcription pipeline.

## Used By
- UI: `/record` page (MediaRecorder), `/upload` page (drag-drop)
- API: `POST /upload`, `POST /memos`

## Core Functions
- `apps/web/src/components/record/recorder.tsx` — single-take MediaRecorder UI with codec fallback (`webm/opus` -> `mp4` -> `ogg/opus`), level meter, save-or-discard
- `apps/web/src/components/record/level-meter.tsx` — canvas RMS meter driven by a Web Audio `AnalyserNode`
- `apps/web/src/components/upload/upload-form.tsx` — drag-drop + queue
- `apps/web/src/components/upload/dropzone.tsx` — `react-dropzone` with audio MIME hints
- `apps/web/src/lib/api-client.ts::uploadFile`, `uploadMemo` — XHR with progress; `uploadMemo` targets `/memos` for parity with future Shortcuts
- `services/api/app/runtime/upload.py` — `POST /upload` and `POST /memos`; both enqueue `service.transcription.run(key)` via `BackgroundTasks` after a successful audio upload
- `services/api/app/service/upload.py` — sanitization, MIME/extension match, audio key construction
- `services/api/app/service/audio_metadata.py` — stamps `x-amz-meta-*` (duration / sample-rate / channels / bit-depth / codec)

## Canonical Files
- Recorder pattern: `apps/web/src/components/record/recorder.tsx`
- Upload service: `services/api/app/service/upload.py`

## Inputs
- multipart form: `file` — audio blob (in-browser recording or file pick) up to 100 MB

## Outputs
- `FileUploadResponse` (`key`, `filename`, `size_bytes`, `size_human`, `content_type`, `uploaded_at`, `metadata`)
- Side effects: audio object at `audio/<YYYY>/<MM>/<safe-filename>--<uuid>.<ext>`; non-audio at `uploads/<safe-filename>` (only the bucket explorer surfaces these); background task enqueued for audio

## Accepted MIME types
- `audio/wav`, `audio/x-wav`, `audio/wave`, `audio/mpeg`, `audio/mp3`, `audio/flac`, `audio/x-flac`, `audio/ogg`, `audio/opus`, `audio/mp4`, `audio/m4a`, `audio/x-m4a`, `audio/aac`, `audio/webm` (recorder output)
- Generic types (images, PDF, text, CSV, JSON, zip, mp4 video) are kept for parity with the bucket explorer.

## Programmatic capture (Shortcuts / Tasker)
The `POST /memos` route mirrors `POST /upload`. To capture from iOS Shortcuts:

```
POST {API_BASE}/memos
Content-Type: multipart/form-data
Body: file=<recorded audio>
```

The response contains the canonical memo key (`audio/<YYYY>/<MM>/<safe-name>--<uuid>.<ext>`). The pipeline runs automatically; the next time the user opens `/memos` the new memo will appear with `Transcribing…` and then flip to `Transcribed` within a few seconds.

## Flow
- User records or drops a file -> client validates type + size -> XHR `POST /upload` (or `/memos`)
- API streams the body in 1 MB chunks with early size-limit rejection
- API sanitizes filename, validates extension matches declared MIME
- API builds the audio key: `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>` (or `uploads/<safe>` for non-audio)
- API extracts audio metadata, stamps it as `x-amz-meta-*`
- API writes via `put_object`, returns `FileUploadResponse`
- For audio uploads: `BackgroundTasks` enqueues `service.transcription.run(key)`

## Edge Cases
- Mic permission denied -> recorder UI toasts and stays in `idle`
- MediaRecorder codec missing -> falls back through the candidate list; if none supported, defaults to `audio/webm` (browser will tell us at runtime)
- File too large -> 413 from API (or client-side rejection)
- Disallowed MIME -> 415
- Empty file -> 400
- B2 unreachable -> 500
- OpenAI key missing -> upload still succeeds; pipeline writes `transcripts/.failed/<stem>.json`

## UX States
- Idle: "Start recording" button
- Recording: live timer + level meter + Stop
- Stopped: inline `<audio controls>` + Save / Discard
- Uploading: disabled button + spinner
- Error: toast

## Verification
- Test files: `services/api/tests/test_upload_conflict.py`, `services/api/tests/test_error_handling.py`
- Quick verify command: `pnpm test:api`
- Full verify command: `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`

## Related Docs
- [Memo library](memo-library.md)
- [Transcription](transcription.md)
- [Memo metadata extraction](memo-metadata.md)
- [Mobile / PWA](mobile-pwa.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

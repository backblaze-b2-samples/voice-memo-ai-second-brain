<!-- last_verified: 2026-05-26 -->
# App Workflows

User journeys through the second brain.

## Record on phone / browser

- User opens the installed PWA (home-screen icon) or navigates to `/record`
- Hits **Start recording** -> grants microphone permission once
- Live level meter and elapsed timer confirm the mic is hot
- Hits **Stop** -> inline `<audio controls>` lets the user re-listen
- Hits **Save to B2** -> blob is POSTed to `/memos`; the user is routed to `/memos/[key]` and the transcription pipeline starts in the background
- See: [Memo capture](features/memo-capture.md), [Mobile / PWA](features/mobile-pwa.md)

## Capture by drag-and-drop

- User navigates to `/upload`
- Drops one or more audio files
- Client validates type + size (max 100MB); rejected files toast with the reason
- Per-file progress bar shows upload status
- API picks `audio/<YYYY>/<MM>/<safe>--<uuid>.<ext>`, extracts metadata, returns the response
- Background tasks fan out (transcription -> tagging + embedding)
- See: [Memo capture](features/memo-capture.md)

## Browse memos

- User navigates to `/memos`
- The grid renders one `MemoCard` per memo, newest-first
- Each card surfaces a status badge (`Transcribing…` / `Transcribed` / `Failed`), the transcript preview, and the LLM-extracted tag chips
- Clicking the title opens the detail page; **Play** swaps in inline `<audio>`; **Download** mints an attachment presigned URL; **Delete** removes the audio plus every sibling artifact in B2
- Bulk-delete supports per-card checkboxes + a header select-all; partial failures are reported with a toast
- See: [Memo library](features/memo-library.md)

## Read a memo (detail)

- User navigates to `/memos/[key]`
- Header shows the filename, B2 key, and pipeline status badge
- **Load audio** mints a 10-min presigned URL and swaps in `<audio controls>`
- **Tags & topics** card shows the LLM-extracted chips (when present)
- **Transcript** card renders segmented Whisper output with timestamp anchors
- **Related memos** card lists the top-5 by cosine similarity
- **Re-transcribe** re-queues the pipeline for failed memos
- **Delete** cascades through transcripts / tags / embeddings
- See: [Memo library](features/memo-library.md), [Transcription](features/transcription.md), [Cross-references](features/cross-references.md)

## Daily / weekly review

- User navigates to `/summary`
- Picks a window (Daily / Weekly) and a period (defaults to today / this ISO week)
- If the summary is cached in B2, it renders immediately
- Otherwise hits **Generate** -> the API aggregates in-window transcripts, calls the chat model, and writes `summaries/<YYYY>/<DD>.md` (or `.../W<WW>.md`) plus a JSON sidecar
- A list of previously-generated summaries lives below the active view; tapping one swaps the period
- See: [Summaries](features/summaries.md)

## Inspect everything (ops)

- User navigates to `/files`
- Page loads the full bucket as a tree; folders for `audio/`, `transcripts/`, `tags/`, `embeddings/`, `summaries/`, `uploads/` (auto-expanded)
- Hover a file row -> preview / download / delete
- Bulk-delete supports per-row and per-folder checkboxes; partial failures reported
- See: [Bucket explorer](features/file-browser.md)

## Watch the dashboard

- User navigates to `/`
- Stats tiles: Total memos / Total minutes / Transcribed / Pending
- Format breakdown chip row
- 7-day chart with **Memos / Minutes** toggle
- Recent memos table with inline play
- Empty bucket renders a single hero CTA pointing at `/record`
- See: [Dashboard](features/dashboard.md)

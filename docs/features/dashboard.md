<!-- last_verified: 2026-05-26 -->
# Feature: Dashboard

## Purpose
Memo-centric overview of the user's second brain: total memos, total minutes captured, how many are transcribed vs pending, recent memo activity, memo formats breakdown.

## Used By
- UI: `/` page
- API: `GET /files/stats`, `GET /memos` (limit 10), `GET /files/stats/activity`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — Total memos / Total minutes / Transcribed / Pending tiles
- `apps/web/src/components/dashboard/format-breakdown.tsx` — memo formats breakdown
- `apps/web/src/components/dashboard/recent-uploads-table.tsx` — last 10 memos with inline-play dialog
- `apps/web/src/components/dashboard/upload-chart.tsx` — last 7 days of memo uploads (toggle: count or minutes)
- `services/api/app/runtime/files.py::stats_endpoint` -> `service.files.get_stats`
- `services/api/app/service/memos.py::get_memo_aggregates` — totals + pipeline status counts

## Canonical Files
- Aggregator: `services/api/app/service/memos.py::get_memo_aggregates`
- Stats endpoint: `services/api/app/runtime/files.py`

## Inputs
- None (everything loaded automatically by the page)

## Outputs
- `GET /files/stats` -> `UploadStats` including `total_memos`, `total_duration_ms`, `transcribed_count`, `pending_count`, `failed_count`, `formats`
- `GET /memos?limit=10` -> recent memos for the recent-activity table
- `GET /files/stats/activity?days=7` -> daily memo counts + minute totals

## Flow
- Page mounts -> three parallel queries (stats, recent memos, activity)
- Stats cards render the four memo-centric tiles
- Recent activity table renders inline-play, linking to `/memos/[key]` on click
- Chart toggles between "memos per day" and "minutes per day"
- Empty bucket -> hero EmptyState pointing at `/record`

## Edge Cases
- API unreachable -> stats fall back to zeros, ErrorState card surfaces a Retry
- Empty bucket -> dedicated EmptyState that links to `/record` instead of the metric tiles
- Pipeline status counts derived from B2 (HEAD per memo); large buckets are capped at 10,000 memos by `list_audio_objects`

## UX States
- Loading: skeleton tiles + table
- Empty: hero card linking to `/record`
- Loaded: tiles + chart + table

## Verification
- Test files: `services/api/tests/test_audio_aggregates.py`, `services/api/tests/test_upload_activity.py`, `services/api/tests/test_recent_files.py`, `services/api/tests/test_download_stats.py`
- Quick verify command: `pnpm test:api`
- Pass criteria: pytest green, no ruff violations

## Related Docs
- [Memo library](memo-library.md)
- [Transcription](transcription.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

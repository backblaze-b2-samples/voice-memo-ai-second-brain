<!-- last_verified: 2026-05-26 -->
# Feature: Memo Metadata Extraction

## Purpose
Read duration, sample rate, channels, bit depth, and codec from an uploaded voice memo and return them in the upload response. Pure-Python: stdlib `wave` for uncompressed WAV, `mutagen` for everything else. No ffmpeg dependency.

## Used By
- API: `POST /upload`, `POST /memos`
- UI: upload progress toasts, `MemoCard` metadata strip, dashboard duration aggregates

## Core Functions
- `services/api/app/service/audio_metadata.py` — `extract_metadata`, `extract_audio_metadata`, `_extract_wav_metadata`, `_extract_mutagen_metadata`, `to_s3_metadata`, `S3_AUDIO_META_KEYS`
- `apps/web/src/components/files/file-metadata-panel.tsx` — structured metadata card on `/files`

## Canonical Files
- Metadata pattern: `services/api/app/service/audio_metadata.py`

## Inputs
- `file_data: bytes` (raw upload payload)
- `filename: str`, `content_type: str`

## Outputs
- `FileMetadataDetail` with audio fields populated when `content_type` matches `audio/*`: `duration_ms`, `sample_rate`, `channels`, `bit_depth`, `codec`
- Side effect: audio fields are also stamped onto the B2 object as `x-amz-meta-*` user metadata (kebab-case keys: `duration-ms`, `sample-rate`, `channels`, `bit-depth`, `codec`). The memo listing reads these back via HEAD instead of re-decoding the audio.

## Supported formats
- `.wav` — stdlib `wave`
- `.mp3` — mutagen
- `.flac` — mutagen
- `.ogg / .opus` — mutagen (`OggVorbis`, `OggOpus`)
- `.m4a / .aac / .mp4` — mutagen (`MP4`)
- `.webm` — mutagen (recorder default)

## Flow
- Upload route receives audio -> `process_upload` calls `extract_metadata` **before** the B2 put
- WAV files route through stdlib `wave`; everything else through mutagen's container sniffer
- `to_s3_metadata` serializes the non-None audio fields into the ASCII kebab-case map
- `upload_file(..., metadata=...)` forwards it to S3 `put_object`
- The memo listing fans out HEAD calls and reads the audio metadata back from `head["Metadata"]`

## Error modes
- Corrupt / unsupported audio -> extractor logs and returns `{}`; upload still succeeds with `None` audio fields. The pipeline never 500s because of a metadata failure.

## Verification
- Test files: covered by `services/api/tests/test_upload_conflict.py` (S3 metadata stamping) and the structural tests.

## Related Docs
- [Memo capture](memo-capture.md)
- [Memo library](memo-library.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)

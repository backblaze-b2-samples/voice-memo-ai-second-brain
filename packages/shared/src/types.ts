export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Audio-specific (populated when content_type starts with audio/)
  duration_ms: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  codec: string | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
  duration_ms: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
  total_memos: number;
  total_audio_assets: number;
  total_duration_ms: number;
  audio_size_bytes: number;
  audio_size_human: string;
  formats: Record<string, number>;
  transcribed_count: number;
  pending_count: number;
  failed_count: number;
}

export type TranscriptionStatus = "pending" | "transcribed" | "failed";

/** A voice memo stored under the `audio/` prefix in B2. */
export interface Memo {
  key: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  created_at: string;
  duration_ms: number | null;
  sample_rate: number | null;
  channels: number | null;
  bit_depth: number | null;
  codec: string | null;
  title_preview: string | null;
  transcription_status: TranscriptionStatus | null;
  tags: string[] | null;
  transcript_preview: string | null;
  embedding_present: boolean | null;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  memo_key: string;
  text: string;
  segments: TranscriptSegment[];
  language: string | null;
  model: string | null;
  generated_at: string;
}

export interface MemoTags {
  memo_key: string;
  tags: string[];
  topics: string[];
  entities: string[];
  model: string | null;
  generated_at: string;
}

export interface RelatedMemo {
  key: string;
  score: number;
  title_preview: string | null;
  transcript_preview: string | null;
}

export type SummaryWindow = "daily" | "weekly";

export interface Summary {
  key: string;
  window: SummaryWindow;
  period: string;
  markdown: string;
  memo_count: number;
  generated_at: string;
  model: string | null;
}

export interface SummaryListEntry {
  key: string;
  window: SummaryWindow;
  period: string;
  memo_count: number;
  generated_at: string;
}

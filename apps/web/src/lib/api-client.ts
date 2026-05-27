import type {
  DailyUploadCount,
  FileMetadata,
  FileUploadResponse,
  Memo,
  MemoTags,
  RelatedMemo,
  Summary,
  SummaryListEntry,
  SummaryWindow,
  Transcript,
  UploadStats,
} from "@voice-memo-ai-second-brain/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

export interface BulkDeleteError {
  Key: string;
  Code: string;
  Message: string;
}

export interface BulkDeleteResult {
  deleted: string[];
  errors: BulkDeleteError[];
}

export async function bulkDeleteFiles(keys: string[]) {
  return apiFetch<BulkDeleteResult>("/files/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
}

// --- Memos (audio/ prefix in B2) ---

export async function getMemos(limit = 100) {
  return apiFetch<Memo[]>(`/memos?limit=${limit}`);
}

export async function getPlaybackUrl(key: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/memos/${key}/playback`,
  );
}

export async function getMemoDownloadUrl(key: string) {
  return apiFetch<{ url: string; expires_in: number }>(
    `/memos/${key}/download`,
  );
}

export async function getMemoTranscript(key: string) {
  return apiFetch<Transcript>(`/memos/${key}/transcript`);
}

export async function getMemoTags(key: string) {
  return apiFetch<MemoTags>(`/memos/${key}/tags`);
}

export async function getRelatedMemos(key: string, topK = 5) {
  return apiFetch<RelatedMemo[]>(`/memos/${key}/related?top_k=${topK}`);
}

export async function deleteMemo(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/memos/${key}`, {
    method: "DELETE",
  });
}

export async function bulkDeleteMemos(keys: string[]) {
  return apiFetch<BulkDeleteResult>("/memos/bulk-delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keys }),
  });
}

export async function retranscribeMemo(key: string) {
  return apiFetch<{ enqueued: boolean; key: string }>(
    `/memos/${key}/transcribe`,
    { method: "POST" },
  );
}

// --- Summaries ---

export async function listSummaries() {
  return apiFetch<SummaryListEntry[]>("/summaries");
}

export async function getSummary(window: SummaryWindow, period: string) {
  return apiFetch<Summary>(`/summaries/${window}/${period}`);
}

export async function generateSummary(
  window: SummaryWindow,
  period?: string,
  force = false,
) {
  return apiFetch<Summary>("/summaries/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ window, period, force }),
  });
}

// --- Upload (shared between drag-drop and in-browser recorder) ---

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/upload`);
    xhr.send(formData);
  });
}

/** Direct memo upload from the in-browser recorder. Mirrors `uploadFile`
 *  but targets `/memos` so iOS Shortcuts and Tasker recipes can hit the
 *  same endpoint (documented in `docs/features/memo-capture.md`). */
export function uploadMemo(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<FileUploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}/memos`);
    xhr.send(formData);
  });
}

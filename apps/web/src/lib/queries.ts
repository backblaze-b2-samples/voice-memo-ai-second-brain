"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  bulkDeleteFiles,
  bulkDeleteMemos,
  deleteFile,
  deleteMemo,
  generateSummary,
  getFiles,
  getFileStats,
  getMemoTags,
  getMemoTranscript,
  getMemos,
  getPreviewUrl,
  getRelatedMemos,
  getSummary,
  getUploadActivity,
  listSummaries,
  retranscribeMemo,
} from "@/lib/api-client";
import type {
  FileMetadata,
  Memo,
  MemoTags,
  RelatedMemo,
  Summary,
  SummaryListEntry,
  SummaryWindow,
  Transcript,
} from "@voice-memo-ai-second-brain/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  memos: (limit?: number) => [...qk.all, "memos", limit ?? 100] as const,
  memoTranscript: (key: string) =>
    [...qk.all, "memo", key, "transcript"] as const,
  memoTags: (key: string) => [...qk.all, "memo", key, "tags"] as const,
  memoRelated: (key: string, topK: number) =>
    [...qk.all, "memo", key, "related", topK] as const,
  summaries: () => [...qk.all, "summaries"] as const,
  summary: (window: SummaryWindow, period: string) =>
    [...qk.all, "summary", window, period] as const,
};

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useBulkDeleteFiles() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keys: string[]) => bulkDeleteFiles(keys),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Memos ---

export function useMemos(limit = 100) {
  return useQuery<Memo[], ApiError>({
    queryKey: qk.memos(limit),
    queryFn: () => getMemos(limit),
    // Pipeline status flips asynchronously after upload — refetch every 30s
    // so the badge transitions to "transcribed" without a manual reload.
    refetchInterval: 30_000,
  });
}

export function useMemoTranscript(key: string | undefined, enabled: boolean) {
  return useQuery<Transcript, ApiError>({
    queryKey: qk.memoTranscript(key ?? ""),
    queryFn: () => getMemoTranscript(key as string),
    enabled: enabled && !!key,
    retry: false,
  });
}

export function useMemoTags(key: string | undefined, enabled: boolean) {
  return useQuery<MemoTags, ApiError>({
    queryKey: qk.memoTags(key ?? ""),
    queryFn: () => getMemoTags(key as string),
    enabled: enabled && !!key,
  });
}

export function useRelatedMemos(
  key: string | undefined,
  topK = 5,
  enabled = true,
) {
  return useQuery<RelatedMemo[], ApiError>({
    queryKey: qk.memoRelated(key ?? "", topK),
    queryFn: () => getRelatedMemos(key as string, topK),
    enabled: enabled && !!key,
  });
}

export function useDeleteMemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => deleteMemo(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useBulkDeleteMemos() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keys: string[]) => bulkDeleteMemos(keys),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useRetranscribeMemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (key: string) => retranscribeMemo(key),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Summaries ---

export function useSummariesList() {
  return useQuery<SummaryListEntry[], ApiError>({
    queryKey: qk.summaries(),
    queryFn: listSummaries,
  });
}

export function useSummary(
  window: SummaryWindow,
  period: string,
  enabled: boolean,
) {
  return useQuery<Summary, ApiError>({
    queryKey: qk.summary(window, period),
    queryFn: () => getSummary(window, period),
    enabled,
    retry: false,
  });
}

export function useGenerateSummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      window: SummaryWindow;
      period?: string;
      force?: boolean;
    }) => generateSummary(args.window, args.period, args.force ?? false),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.summaries() });
    },
  });
}

"use client";

import { CheckCircle2, Clock, AlertCircle } from "lucide-react";

import type { TranscriptionStatus } from "@voice-memo-ai-second-brain/shared";

interface MemoStatusBadgeProps {
  status: TranscriptionStatus | null | undefined;
  className?: string;
}

/**
 * Compact status pill rendered on memo cards + the detail header.
 * Derived from the existence of `transcripts/<stem>.json` (or its
 * `.failed/` sibling). The transcription pipeline is the slowest of the
 * three pipeline stages, so we surface its state and treat the downstream
 * tagging + embedding stages as "follow on success".
 */
export function MemoStatusBadge({ status, className }: MemoStatusBadgeProps) {
  if (!status || status === "pending") {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground ${className ?? ""}`}
      >
        <Clock className="h-3 w-3 animate-pulse" />
        Transcribing…
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span
        className={`inline-flex items-center gap-1 rounded-full bg-destructive/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-destructive ${className ?? ""}`}
      >
        <AlertCircle className="h-3 w-3" />
        Failed
      </span>
    );
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-primary ${className ?? ""}`}
    >
      <CheckCircle2 className="h-3 w-3" />
      Transcribed
    </span>
  );
}

"use client";

import { Skeleton } from "@/components/ui/skeleton";
import type { Transcript } from "@voice-memo-ai-second-brain/shared";

interface TranscriptViewProps {
  transcript: Transcript | undefined;
  isLoading: boolean;
  isPending: boolean; // true when transcription hasn't run yet
}

function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * Renders the segmented transcript with timestamp anchors. When the
 * pipeline hasn't produced a transcript yet (`isPending`), shows a
 * friendly placeholder; on error/missing, surfaces the same.
 */
export function TranscriptView({
  transcript,
  isLoading,
  isPending,
}: TranscriptViewProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-4 w-full" />
        ))}
      </div>
    );
  }
  if (isPending || !transcript) {
    return (
      <p className="text-sm italic text-muted-foreground">
        Transcript will appear here once the pipeline finishes — usually a
        few seconds after upload.
      </p>
    );
  }
  if (transcript.segments.length === 0) {
    return (
      <p className="text-sm leading-relaxed whitespace-pre-wrap">
        {transcript.text}
      </p>
    );
  }

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {transcript.segments.map((seg, i) => (
        <div key={i} className="flex gap-3">
          <a
            href={`#t=${seg.start}`}
            className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground hover:text-foreground"
            aria-label={`Jump to ${formatTimestamp(seg.start)}`}
          >
            {formatTimestamp(seg.start)}
          </a>
          <p className="flex-1">{seg.text}</p>
        </div>
      ))}
    </div>
  );
}

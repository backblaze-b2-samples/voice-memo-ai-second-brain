"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Inbox, Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { ApiError, getPlaybackUrl } from "@/lib/api-client";
import { useMemos } from "@/lib/queries";
import { formatDate, formatDuration } from "@/lib/utils";
import type { Memo } from "@voice-memo-ai-second-brain/shared";

/**
 * Memo-first recent uploads table for the dashboard.
 *
 * Sources rows from `useMemos` (audio prefix only — not the full bucket),
 * renders duration / format / date, and lets the user preview a track inline
 * via a small Dialog holding a native `<audio controls>` fed by a short-lived
 * presigned URL from `getPlaybackUrl`. The loading/error toast pattern mirrors
 * `components/memos/memo-card.tsx` for consistency.
 */
export function RecentUploadsTable() {
  const { data: memos = [], isLoading, error, refetch } = useMemos(10);
  const [activeMemo, setActiveMemo] = useState<Memo | null>(null);
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const handlePlay = async (memo: Memo) => {
    setLoadingKey(memo.key);
    try {
      const { url } = await getPlaybackUrl(memo.key);
      setAudioSrc(url);
      setActiveMemo(memo);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load playback URL";
      toast.error(detail);
    } finally {
      setLoadingKey(null);
    }
  };

  const handleOpenChange = (open: boolean) => {
    if (!open) {
      setActiveMemo(null);
      setAudioSrc(null);
    }
  };

  const filenameFor = (memo: Memo) =>
    memo.title_preview ?? memo.key.split("/").pop() ?? memo.key;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Memos</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/memos"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : memos.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No memos yet"
            description="Record one or upload an audio file to get started."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[38%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Filename
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Duration
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Format
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Date
                </TableHead>
                <TableHead className="w-[12%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  <span className="sr-only">Play</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {memos.map((memo) => (
                <TableRow key={memo.key} className="table-row-hover">
                  <TableCell className="font-medium">
                    <div className="truncate">{filenameFor(memo)}</div>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                    {formatDuration(memo.duration_ms)}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap uppercase text-xs">
                    {memo.codec ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(memo.created_at)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handlePlay(memo)}
                      disabled={loadingKey === memo.key}
                      aria-label={`Play ${filenameFor(memo)}`}
                    >
                      <Play className="h-3.5 w-3.5" />
                      {loadingKey === memo.key ? "Loading..." : "Play"}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={activeMemo !== null} onOpenChange={handleOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="truncate font-mono text-sm">
              {activeMemo ? filenameFor(activeMemo) : ""}
            </DialogTitle>
          </DialogHeader>
          {audioSrc ? (
            <audio controls autoPlay src={audioSrc} className="w-full" />
          ) : null}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

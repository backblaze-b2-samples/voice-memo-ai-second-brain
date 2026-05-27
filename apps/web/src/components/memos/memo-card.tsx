"use client";

import Link from "next/link";
import { useState } from "react";
import { Download, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Waveform } from "./waveform";
import { MemoStatusBadge } from "./memo-status-badge";
import { TagChip } from "./tag-chip";
import {
  ApiError,
  getMemoDownloadUrl,
  getPlaybackUrl,
} from "@/lib/api-client";
import { useDeleteMemo } from "@/lib/queries";
import { formatDate, formatDuration } from "@/lib/utils";
import type { Memo } from "@voice-memo-ai-second-brain/shared";

interface MemoCardProps {
  memo: Memo;
  selected?: boolean;
  onToggleSelect?: (key: string) => void;
}

/**
 * The Voice Memo card primitive. Renders one memo with:
 *   - a status badge (Transcribing… / Transcribed / Failed)
 *   - a metadata strip (duration · sample rate · channels · created)
 *   - up to 6 LLM-extracted tag chips
 *   - inline `<audio>` playback gated by a short-lived presigned URL
 *   - View / Download / Delete actions
 *
 * Click-through to `/memos/[key]` reveals the full transcript, all tags,
 * and related memos.
 */
export function MemoCard({
  memo,
  selected = false,
  onToggleSelect,
}: MemoCardProps) {
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [loadingPlayback, setLoadingPlayback] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const deleteMutation = useDeleteMemo();

  const handlePlay = async () => {
    if (audioSrc) return;
    setLoadingPlayback(true);
    try {
      const { url } = await getPlaybackUrl(memo.key);
      setAudioSrc(url);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load playback URL";
      toast.error(detail);
    } finally {
      setLoadingPlayback(false);
    }
  };

  const handleDownload = async () => {
    try {
      const { url } = await getMemoDownloadUrl(memo.key);
      window.open(url, "_blank");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to get download URL";
      toast.error(detail);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate(memo.key, {
      onSuccess: () => {
        toast.success("Memo deleted");
        setConfirmDelete(false);
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to delete";
        toast.error(detail);
      },
    });
  };

  const metaParts: string[] = [];
  if (memo.duration_ms) metaParts.push(formatDuration(memo.duration_ms));
  if (memo.sample_rate) metaParts.push(`${(memo.sample_rate / 1000).toFixed(1)} kHz`);
  if (memo.channels) {
    metaParts.push(memo.channels === 1 ? "mono" : `${memo.channels} ch`);
  }
  metaParts.push(formatDate(memo.created_at));

  const tags = memo.tags ?? [];
  const detailHref = `/memos/${memo.key}`;

  return (
    <>
      <Card
        className={`card-hover ${selected ? "ring-2 ring-primary" : ""}`}
      >
        <CardContent className="space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            {onToggleSelect && (
              <Checkbox
                checked={selected}
                onCheckedChange={() => onToggleSelect(memo.key)}
                aria-label={`Select ${memo.title_preview ?? memo.key}`}
                className="mt-1"
              />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <Link
                  href={detailHref}
                  className="line-clamp-2 text-sm font-medium font-mono hover:underline"
                >
                  {memo.title_preview ?? memo.key.split("/").pop()}
                </Link>
                <MemoStatusBadge status={memo.transcription_status} />
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {metaParts.join(" · ")}
              </p>
            </div>
          </div>

          <Waveform durationMs={memo.duration_ms} />

          {memo.transcript_preview && (
            <p className="line-clamp-2 text-xs text-muted-foreground italic">
              {memo.transcript_preview}
            </p>
          )}

          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.slice(0, 6).map((t) => (
                <TagChip key={t} label={t} />
              ))}
              {tags.length > 6 && (
                <span className="text-[11px] text-muted-foreground">
                  +{tags.length - 6}
                </span>
              )}
            </div>
          )}

          {audioSrc ? (
            <audio controls src={audioSrc} className="w-full" autoPlay />
          ) : (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={handlePlay}
                disabled={loadingPlayback}
              >
                <Play className="h-3.5 w-3.5" />
                {loadingPlayback ? "Loading..." : "Play"}
              </Button>
              <Button size="sm" variant="outline" asChild>
                <Link href={detailHref}>View</Link>
              </Button>
              <Button size="sm" variant="outline" onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmDelete(true)}
                className="ml-auto text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete memo?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the audio plus its transcript, tags,
              and embedding from B2. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

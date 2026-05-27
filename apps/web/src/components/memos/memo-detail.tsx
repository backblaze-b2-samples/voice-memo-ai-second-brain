"use client";

import { useState } from "react";
import { Download, Trash2, RefreshCw, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TranscriptView } from "./transcript-view";
import { TagChip } from "./tag-chip";
import { RelatedMemos } from "./related-memos";
import { MemoStatusBadge } from "./memo-status-badge";
import {
  ApiError,
  getMemoDownloadUrl,
  getPlaybackUrl,
} from "@/lib/api-client";
import {
  useDeleteMemo,
  useMemoTags,
  useMemoTranscript,
  useRetranscribeMemo,
} from "@/lib/queries";

interface MemoDetailProps {
  memoKey: string;
}

/**
 * Full memo view. Owns the audio player, transcript reader, tag chips,
 * related-memos card, and delete affordance. Pulled out of the page
 * component so the route file stays a thin shell.
 */
export function MemoDetail({ memoKey }: MemoDetailProps) {
  const router = useRouter();
  const [audioSrc, setAudioSrc] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const transcriptQuery = useMemoTranscript(memoKey, true);
  const tagsQuery = useMemoTags(memoKey, true);
  const deleteMutation = useDeleteMemo();
  const retranscribeMutation = useRetranscribeMemo();

  const handlePlay = async () => {
    if (audioSrc) return;
    try {
      const { url } = await getPlaybackUrl(memoKey);
      setAudioSrc(url);
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to load playback URL";
      toast.error(detail);
    }
  };

  const handleDownload = async () => {
    try {
      const { url } = await getMemoDownloadUrl(memoKey);
      window.open(url, "_blank");
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Failed to get download URL";
      toast.error(detail);
    }
  };

  const handleDelete = () => {
    deleteMutation.mutate(memoKey, {
      onSuccess: () => {
        toast.success("Memo deleted");
        router.push("/memos");
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to delete";
        toast.error(detail);
      },
    });
  };

  const handleRetranscribe = () => {
    retranscribeMutation.mutate(memoKey, {
      onSuccess: () => {
        toast.success("Re-queued transcription");
        transcriptQuery.refetch();
      },
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to enqueue";
        toast.error(detail);
      },
    });
  };

  const filename = memoKey.split("/").pop() ?? memoKey;
  const tags = tagsQuery.data?.tags ?? [];
  const topics = tagsQuery.data?.topics ?? [];
  const entities = tagsQuery.data?.entities ?? [];

  const transcriptIsPending =
    !transcriptQuery.isLoading &&
    transcriptQuery.error instanceof ApiError &&
    transcriptQuery.error.isNotFound;

  const status = transcriptQuery.data
    ? "transcribed"
    : transcriptIsPending
      ? "pending"
      : transcriptQuery.error
        ? "failed"
        : "pending";

  return (
    <>
      <div className="space-y-6">
        <div className="border-b border-border pb-5 space-y-2">
          <div className="flex items-center gap-2">
            <Button asChild size="sm" variant="ghost" className="h-7 px-2">
              <Link href="/memos">
                <ArrowLeft className="h-3.5 w-3.5" />
                All memos
              </Link>
            </Button>
            <MemoStatusBadge status={status} />
          </div>
          <h1 className="page-title font-mono break-all">{filename}</h1>
          <p className="text-xs text-muted-foreground">{memoKey}</p>
        </div>

        <Card>
          <CardContent className="p-5 space-y-3">
            {audioSrc ? (
              <audio controls src={audioSrc} className="w-full" autoPlay />
            ) : (
              <Button size="sm" variant="outline" onClick={handlePlay}>
                Load audio
              </Button>
            )}
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
                Download
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleRetranscribe}
                disabled={retranscribeMutation.isPending}
              >
                <RefreshCw
                  className={`h-3.5 w-3.5 ${retranscribeMutation.isPending ? "animate-spin" : ""}`}
                />
                Re-transcribe
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setConfirmDelete(true)}
                className="ml-auto text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </div>
          </CardContent>
        </Card>

        {(tags.length > 0 || topics.length > 0 || entities.length > 0) && (
          <Card>
            <CardHeader className="border-b border-border py-4 px-5">
              <CardTitle className="card-title">Tags & topics</CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-3">
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {tags.map((t) => (
                    <TagChip key={t} label={t} />
                  ))}
                </div>
              )}
              {topics.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {topics.map((t) => (
                    <TagChip key={t} label={t} variant="topic" />
                  ))}
                </div>
              )}
              {entities.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {entities.map((t) => (
                    <TagChip key={t} label={t} variant="entity" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="border-b border-border py-4 px-5">
            <CardTitle className="card-title">Transcript</CardTitle>
          </CardHeader>
          <CardContent className="p-5">
            <TranscriptView
              transcript={transcriptQuery.data}
              isLoading={transcriptQuery.isLoading}
              isPending={transcriptIsPending}
            />
          </CardContent>
        </Card>

        <RelatedMemos memoKey={memoKey} />
      </div>

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

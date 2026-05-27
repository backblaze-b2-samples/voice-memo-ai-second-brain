"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRelatedMemos } from "@/lib/queries";

interface RelatedMemosProps {
  memoKey: string;
}

/**
 * Top-5 related memos by cosine similarity over the OpenAI embeddings
 * stored in B2. Hidden when nothing relates (yet) — e.g. there's only one
 * memo in the bucket, or the embedding pipeline hasn't run.
 */
export function RelatedMemos({ memoKey }: RelatedMemosProps) {
  const { data, isLoading } = useRelatedMemos(memoKey, 5);

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Related memos</CardTitle>
        </CardHeader>
        <CardContent className="p-5 space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }
  if (!data || data.length === 0) {
    return null;
  }
  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Related memos</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ul className="divide-y divide-border">
          {data.map((r) => (
            <li key={r.key} className="px-5 py-3 hover:bg-muted/30">
              <Link
                href={`/memos/${r.key}`}
                className="flex items-center justify-between gap-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-mono text-sm">
                    {r.title_preview ?? r.key.split("/").pop()}
                  </p>
                  {r.transcript_preview && (
                    <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground italic">
                      {r.transcript_preview}
                    </p>
                  )}
                </div>
                <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                  {(r.score * 100).toFixed(0)}%
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
              </Link>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

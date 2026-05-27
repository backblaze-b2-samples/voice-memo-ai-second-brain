"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ApiError,
} from "@/lib/api-client";
import {
  useGenerateSummary,
  useSummariesList,
  useSummary,
} from "@/lib/queries";
import type { SummaryWindow } from "@voice-memo-ai-second-brain/shared";

function defaultPeriod(window: SummaryWindow): string {
  const now = new Date();
  if (window === "daily") {
    return now.toISOString().slice(0, 10);
  }
  // ISO week number computed without external deps.
  const target = new Date(
    Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()),
  );
  const dayNum = target.getUTCDay() || 7;
  target.setUTCDate(target.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(target.getUTCFullYear(), 0, 1));
  const week = Math.ceil(
    ((+target - +yearStart) / 86400000 + 1) / 7,
  );
  return `${target.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

export function SummaryView() {
  const [window, setWindow] = useState<SummaryWindow>("daily");
  const [period, setPeriod] = useState<string>(() => defaultPeriod("daily"));
  const list = useSummariesList();
  const summary = useSummary(window, period, true);
  const generate = useGenerateSummary();

  const handleWindowChange = (next: SummaryWindow) => {
    setWindow(next);
    setPeriod(defaultPeriod(next));
  };

  const handleGenerate = (force = false) => {
    generate.mutate(
      { window, period, force },
      {
        onSuccess: () => {
          toast.success("Summary generated");
          summary.refetch();
        },
        onError: (err) => {
          const detail =
            err instanceof ApiError
              ? err.message
              : "Summary generation failed";
          toast.error(detail);
        },
      },
    );
  };

  const isNotFound =
    summary.error instanceof ApiError && summary.error.isNotFound;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Summary</CardTitle>
        </CardHeader>
        <CardContent className="p-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Tabs
              value={window}
              onValueChange={(v) => handleWindowChange(v as SummaryWindow)}
            >
              <TabsList className="h-8 p-0.5">
                <TabsTrigger value="daily" className="h-7 px-3 text-xs">
                  Daily
                </TabsTrigger>
                <TabsTrigger value="weekly" className="h-7 px-3 text-xs">
                  Weekly
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <input
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="h-8 rounded-md border border-border bg-background px-2 font-mono text-xs"
              aria-label="Period"
            />
            <Button
              size="sm"
              onClick={() => handleGenerate(false)}
              disabled={generate.isPending}
              className="h-8"
            >
              <Sparkles className="h-3.5 w-3.5" />
              {summary.data ? "Regenerate" : "Generate"}
            </Button>
          </div>

          {summary.isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
          )}
          {isNotFound && !generate.isPending && (
            <p className="text-sm italic text-muted-foreground">
              No summary cached for {period}. Hit Generate to create one.
            </p>
          )}
          {summary.data && (
            <article className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap font-sans">
              {summary.data.markdown}
            </article>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Cached summaries</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {list.isLoading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          ) : list.data && list.data.length > 0 ? (
            <ul className="divide-y divide-border">
              {list.data.map((entry) => (
                <li key={entry.key} className="px-5 py-3">
                  <button
                    onClick={() => {
                      setWindow(entry.window);
                      setPeriod(entry.period);
                    }}
                    className="flex w-full items-center justify-between gap-3 hover:text-foreground"
                  >
                    <span className="font-mono text-xs">
                      {entry.window} — {entry.period}
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {entry.memo_count}{" "}
                      {entry.memo_count === 1 ? "memo" : "memos"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-5 py-4 text-sm italic text-muted-foreground">
              No summaries yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

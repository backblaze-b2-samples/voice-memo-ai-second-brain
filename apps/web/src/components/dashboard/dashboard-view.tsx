"use client";

import Link from "next/link";
import { Mic, AudioLines } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { FormatBreakdown } from "@/components/dashboard/format-breakdown";
import { RecentUploadsTable } from "@/components/dashboard/recent-uploads-table";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { UploadChart } from "@/components/dashboard/upload-chart";
import { useFileStats } from "@/lib/queries";

/**
 * Dashboard body. Splits into two layouts driven by `useFileStats()`:
 *
 *  - **Empty bucket** (`total_audio_assets === 0`, not loading/erroring):
 *    a single hero card prompting the first upload. We deliberately keep
 *    `StatsCards`/charts/table off-screen here — they're all-zero on an
 *    empty bucket and dilute the call to action.
 *  - **Populated**: the usual StatsCards + FormatBreakdown + chart/table grid.
 *
 * Errors and the initial loading state both fall through to the populated
 * layout so the child components can render their own skeletons / error UI
 * (consistent with the rest of the app).
 */
export function DashboardView() {
  const { data: stats, isLoading, error } = useFileStats();
  const total = stats?.total_memos ?? stats?.total_audio_assets ?? 0;
  const isEmpty = !isLoading && !error && total === 0;

  if (isEmpty) {
    return (
      <Card className="animate-fade-in-up">
        <CardContent className="p-0">
          <EmptyState
            icon={AudioLines}
            title="No memos yet — record your first one"
            description="Record a quick voice memo in the browser or drop an existing audio file in Upload. Transcription, tagging, and cross-references run automatically."
            action={
              <Button asChild size="sm" className="h-8">
                <Link href="/record">
                  <Mic className="h-3.5 w-3.5" />
                  Record a memo
                </Link>
              </Button>
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <StatsCards />
      <FormatBreakdown />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <UploadChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentUploadsTable />
        </div>
      </div>
    </>
  );
}

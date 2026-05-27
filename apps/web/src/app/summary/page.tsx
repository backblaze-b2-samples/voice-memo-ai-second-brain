import { SummaryView } from "@/components/summary/summary-view";

export default function SummaryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Summary</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Daily and weekly AI-generated rollups of your voice memos. Stored
          as markdown in B2 under <code className="font-mono">summaries/</code>.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <SummaryView />
      </div>
    </div>
  );
}

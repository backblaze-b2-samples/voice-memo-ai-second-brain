import { Recorder } from "@/components/record/recorder";

export default function RecordPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Record</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Capture a quick voice memo from your browser. Save it to B2 and the
          transcription + tagging pipeline kicks off automatically.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <Recorder />
      </div>
    </div>
  );
}

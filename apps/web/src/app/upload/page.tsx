import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Drag audio files in or click to browse. Up to 100 MB per file. Audio
          uploads land under <code className="font-mono text-xs">audio/</code>{" "}
          and kick off the transcription + tagging pipeline automatically;
          anything else lands under <code className="font-mono text-xs">uploads/</code>{" "}
          and only shows up in Files.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}

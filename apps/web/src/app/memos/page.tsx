import Link from "next/link";
import { Mic, Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MemosView } from "@/components/memos/memos-view";

export default function MemosPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Memos</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every voice memo in your second brain — transcribed, tagged, and
            cross-referenced.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild size="sm" variant="outline" className="h-8">
            <Link href="/upload">
              <Upload className="h-3.5 w-3.5" />
              Upload
            </Link>
          </Button>
          <Button asChild size="sm" className="h-8">
            <Link href="/record">
              <Mic className="h-3.5 w-3.5" />
              Record
            </Link>
          </Button>
        </div>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <MemosView />
      </div>
    </div>
  );
}

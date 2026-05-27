"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MemoCard } from "@/components/memos/memo-card";
import { Section } from "./section";
import type { Memo } from "@voice-memo-ai-second-brain/shared";

// Static demo memo — keys, sizes, timestamps are fabricated. Play /
// Download will toast a failure when clicked since the key doesn't
// resolve in B2; that's the intended showcase behavior.
const sampleMemo: Memo = {
  key: "audio/2026/05/00000000-0000-4000-8000-000000000001.wav",
  size_bytes: 287_440,
  size_human: "280.7 KB",
  content_type: "audio/wav",
  created_at: "2026-05-20T14:23:00.000Z",
  duration_ms: 12_400,
  sample_rate: 44_100,
  channels: 2,
  bit_depth: 16,
  codec: "wav",
  title_preview: "morning-thought.wav",
  transcription_status: "transcribed",
  tags: ["second brain", "voice memo", "writing", "todo"],
  transcript_preview:
    "Quick reminder to flesh out the second-brain capture flow this afternoon.",
  embedding_present: true,
};

export function DesignMemoCard() {
  return (
    <Section
      id="memo-card"
      title="Memo Card"
      description="The default primitive for rendering a voice memo. Surfaces the pipeline status badge, metadata strip, tag chips, transcript preview, and Play / View / Download / Delete actions. Compose into any grid scoped to the audio/ prefix."
    >
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Sample memo</CardTitle>
        </CardHeader>
        <CardContent className="p-5">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <MemoCard memo={sampleMemo} />
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Source: <code className="font-mono">apps/web/src/components/memos/memo-card.tsx</code> ·
            also documented in <code className="font-mono">docs/features/memo-library.md</code>.
          </p>
        </CardContent>
      </Card>
    </Section>
  );
}

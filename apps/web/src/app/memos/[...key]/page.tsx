import { MemoDetail } from "@/components/memos/memo-detail";

interface MemoDetailPageProps {
  params: Promise<{ key: string[] }>;
}

/**
 * Memo detail route. Catch-all dynamic segment because memo keys contain
 * slashes (e.g. `audio/2026/05/foo--abc.wav`). Server component reassembles
 * the URL segments back into the canonical key the API expects.
 */
export default async function MemoDetailPage({ params }: MemoDetailPageProps) {
  const { key } = await params;
  const memoKey = key.join("/");

  return (
    <div className="space-y-6 animate-fade-in">
      <MemoDetail memoKey={memoKey} />
    </div>
  );
}

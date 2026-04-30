import { notFound } from "next/navigation";

import { ReplayPlayer } from "@/components/replay/replay-player";
import { getReplayTrace } from "@/lib/replay";

export const dynamic = "force-dynamic";

export default async function ReplayPage({
  params,
}: {
  params: { id: string };
}) {
  const trace = await getReplayTrace(params.id);
  if (!trace) notFound();
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">
          Replay debugger
        </h1>
        <p className="text-muted-foreground font-mono text-xs">
          {trace.id} · conversation {trace.conversation_id}
        </p>
      </header>
      <ReplayPlayer trace={trace} />
    </main>
  );
}

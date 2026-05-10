import { notFound } from "next/navigation";

import { ReplayPlayer } from "@/components/replay/replay-player";
import { SectionDegraded } from "@/components/section-states";
import { getReplayTrace } from "@/lib/replay";

export const dynamic = "force-dynamic";

export default async function ReplayPage({
  params,
}: {
  params: { id: string };
}) {
  const trace = await getReplayTrace(params.id).catch((error: unknown) => {
    const message =
      error instanceof Error ? error.message : "Replay trace could not be loaded.";
    return { degradedReason: message };
  });
  if (trace && "degradedReason" in trace) {
    return (
      <main className="container mx-auto p-6" data-testid="replay-page">
        <SectionDegraded
          title="Replay"
          description="Replay evidence is unavailable. Studio needs the source trace before it can render a replay timeline."
          evidence={trace.degradedReason}
          primaryAction={{ label: "Back to traces", href: "/traces" }}
        />
      </main>
    );
  }
  if (!trace) notFound();
  return (
    <main className="container mx-auto p-6" data-testid="replay-page">
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

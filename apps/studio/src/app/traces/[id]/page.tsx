import { notFound } from "next/navigation";

import { getTrace } from "@/lib/traces";
import { FIXTURE_REPLAY_ID } from "@/lib/replay";
import { TraceWaterfall } from "@/components/trace/waterfall";

export const dynamic = "force-dynamic";

export default async function TracePage({
  params,
}: {
  params: { id: string };
}) {
  const trace = await getTrace(params.id);
  if (!trace) notFound();
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Trace</h1>
          <p className="text-muted-foreground font-mono text-xs">{trace.id}</p>
        </div>
        <a
          href={`/replay/${FIXTURE_REPLAY_ID}`}
          className="rounded border bg-white px-3 py-1.5 text-sm hover:bg-zinc-50"
        >
          Replay
        </a>
      </header>
      <TraceWaterfall trace={trace} />
    </main>
  );
}

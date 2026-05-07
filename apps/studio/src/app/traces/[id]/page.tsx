import { notFound } from "next/navigation";

import { getTrace } from "@/lib/traces";
import { TraceTheater } from "@/components/trace/trace-theater";

export const dynamic = "force-dynamic";

export default async function TracePage({
  params,
}: {
  params: { id: string };
}) {
  const trace = await getTrace(params.id);
  if (!trace) notFound();
  return (
    <main className="p-6">
      <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Observe / Trace Theater
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            {trace.title ?? "Trace detail"}
          </h1>
          <p className="text-muted-foreground font-mono text-xs">{trace.id}</p>
        </div>
        <a
          className="rounded-md border bg-card px-3 py-1.5 text-sm target-transition hover:bg-muted"
          href={`/replay/${encodeURIComponent(trace.id)}`}
        >
          Open replay
        </a>
      </header>
      <TraceTheater trace={trace} />
    </main>
  );
}

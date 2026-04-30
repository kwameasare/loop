import { notFound } from "next/navigation";
import { getTrace } from "@/lib/traces";
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
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Trace</h1>
        <p className="text-muted-foreground font-mono text-xs">{trace.id}</p>
      </header>
      <TraceWaterfall trace={trace} />
    </main>
  );
}

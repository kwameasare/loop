import { TraceList } from "@/components/trace/trace-list";
import { FIXTURE_TRACES } from "@/lib/traces";

export const dynamic = "force-dynamic";

export default function TracesPage(): JSX.Element {
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Traces</h1>
        <p className="text-muted-foreground text-sm">
          Browse recent traces. Filter by status or agent and click into any
          trace to see its waterfall.
        </p>
      </header>
      <TraceList traces={FIXTURE_TRACES} initialPageSize={20} />
    </main>
  );
}

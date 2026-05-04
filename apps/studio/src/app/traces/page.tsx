"use client";

/**
 * P0.3: ``/traces`` — recent runtime traces.
 *
 * Wires the TraceList to ``GET /v1/workspaces/{id}/traces`` (P0.4
 * route, shipped). cp's TraceSummary is sparser than the studio's —
 * agent_name + root_name fall back to the agent_id / a short turn
 * label until cp emits display strings.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { TraceList } from "@/components/trace/trace-list";
import { searchTraces, type TraceSummary } from "@/lib/traces";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function TracesPage(): JSX.Element {
  return (
    <RequireAuth>
      <TracesPageBody />
    </RequireAuth>
  );
}

function TracesPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [traces, setTraces] = useState<TraceSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void searchTraces(active.id, { page_size: 100 })
      .then((res) => {
        if (cancelled) return;
        setTraces(res.traces);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load traces");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active) {
    return (
      <main className="container mx-auto p-6">
        <p
          className="text-sm text-muted-foreground"
          data-testid="traces-loading"
        >
          Loading traces…
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      </main>
    );
  }
  if (traces === null) {
    return (
      <main className="container mx-auto p-6">
        <p
          className="text-sm text-muted-foreground"
          data-testid="traces-loading"
        >
          Loading traces…
        </p>
      </main>
    );
  }
  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Traces</h1>
        <p className="text-muted-foreground text-sm">
          Browse recent traces. Filter by status or agent and click into any
          trace to see its waterfall.
        </p>
      </header>
      <TraceList traces={traces} initialPageSize={20} />
    </main>
  );
}

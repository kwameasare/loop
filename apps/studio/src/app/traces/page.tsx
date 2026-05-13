"use client";

/**
 * P0.3: ``/traces`` — recent runtime traces.
 *
 * Wires the TraceList to ``GET /v1/workspaces/{id}/traces`` (P0.4
 * route, shipped). cp's TraceSummary is sparser than the studio's —
 * agent_name + root_name fall back to the agent_id / a short turn
 * label until cp emits display strings.
 */

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import { TraceList } from "@/components/trace/trace-list";
import { searchTraces, type TraceSummary } from "@/lib/traces";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function TracesPage(): JSX.Element {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="container mx-auto p-6">
            <p
              className="text-sm text-muted-foreground"
              data-testid="traces-loading"
            >
              Loading traces…
            </p>
          </main>
        }
      >
        <TracesPageBody />
      </Suspense>
    </RequireAuth>
  );
}

function TracesPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const searchParams = useSearchParams();
  const initialAgentId = searchParams.get("agent_id") ?? undefined;
  const initialStatus = traceStatusFromParams(searchParams);
  const initialQuery = traceQueryFromParams(searchParams);
  const focusMessage = traceFocusMessage(searchParams);
  const activeWorkspaceId = active?.id;
  const [traces, setTraces] = useState<TraceSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void searchTraces(activeWorkspaceId, {
      ...(initialAgentId ? { agent_id: initialAgentId } : {}),
      page_size: 100,
    })
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
  }, [activeWorkspaceId, initialAgentId]);

  if (wsLoading) {
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
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Traces" />;
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <SectionDegraded
          title="Traces"
          description="Trace evidence is unavailable. Studio will not show fixture turns or call this workspace empty when the trace backend cannot be reached."
          evidence={error}
        />
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
      <TraceList
        traces={traces}
        focusMessage={focusMessage}
        initialAgentId={initialAgentId}
        initialPageSize={20}
        initialQuery={initialQuery}
        initialStatus={initialStatus}
      />
    </main>
  );
}

function traceStatusFromParams(
  searchParams: URLSearchParams,
): "all" | "ok" | "error" {
  if (searchParams.get("only_errors") === "true") return "error";
  if (searchParams.get("filter") === "failed") return "error";
  return "all";
}

function traceQueryFromParams(
  searchParams: URLSearchParams,
): string | undefined {
  const span = searchParams.get("span");
  if (span) return span;
  const filter = searchParams.get("filter");
  if (filter && filter !== "failed") return filter;
  return undefined;
}

function traceFocusMessage(searchParams: URLSearchParams): string | undefined {
  if (searchParams.get("only_errors") === "true") {
    return "Opened from evidence link: showing error traces.";
  }
  const mode = searchParams.get("mode");
  if (mode === "replay") {
    return "Opened in replay mode: select a trace to replay or compare.";
  }
  const span = searchParams.get("span");
  if (span) {
    return `Opened from evidence link: filtering traces by ${span} spans.`;
  }
  const filter = searchParams.get("filter");
  if (filter) {
    return `Opened from evidence link: filtering traces by ${filter}.`;
  }
  return undefined;
}

"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { StatePanel } from "@/components/target";
import { AgentXrayPanel } from "@/components/trace/xray/agent-xray-panel";
import { fetchAgentXrayTraces } from "@/lib/agent-xray";
import type { Trace } from "@/lib/traces";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function XrayPage(): JSX.Element {
  return (
    <RequireAuth>
      <XrayPageBody />
    </RequireAuth>
  );
}

function XrayPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [traces, setTraces] = useState<Trace[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setTraces(null);
    setError(null);
    void fetchAgentXrayTraces(active.id)
      .then((next) => {
        if (cancelled) return;
        setTraces(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load X-Ray");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active || (!traces && !error)) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-muted-foreground">Loading Agent X-Ray...</p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-7xl p-6">
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      </main>
    );
  }
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <header className="max-w-3xl">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          Observe / Agent X-Ray
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          See what the agent actually does
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          X-Ray aggregates representative traces into evidence-backed claims
          about tools, retrieval, memory, cost, and unsupported telemetry.
        </p>
      </header>
      {traces && traces.length > 0 ? (
        <AgentXrayPanel trace={traces} />
      ) : (
        <StatePanel state="empty" title="No traces available">
          Run production or simulator turns before X-Ray can derive observed
          behavior.
        </StatePanel>
      )}
    </main>
  );
}

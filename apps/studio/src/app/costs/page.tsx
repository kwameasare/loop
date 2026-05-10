"use client";

/**
 * P0.3: ``/costs`` — workspace cost dashboard.
 *
 * Wires the dashboard to ``GET /v1/workspaces/{id}/usage`` (P0.4
 * route, shipped). The cp emits a minimal usage event shape today
 * (workspace_id, metric, quantity, timestamp_ms); fuller dimensions
 * (agent_id, channel, model) are mapped through ``fetchUsageRecords``
 * and degrade to "all agents" / unknown channel until cp's runtime
 * emits them.
 */

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { CostPageClient } from "@/components/cost/cost-page-client";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  fetchUsageRecords,
  monthBoundsUTC,
  type UsageRecord,
} from "@/lib/costs";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function CostsPage(): JSX.Element {
  return (
    <RequireAuth>
      <CostsPageBody />
    </RequireAuth>
  );
}

function CostsPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const activeWorkspaceId = active?.id;
  const [records, setRecords] = useState<UsageRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const nowMs = useMemo(() => Date.now(), []);
  // Pull the full month-to-date window so the KPI cards have the
  // data they need; the dashboard sub-components further filter
  // client-side.
  const window_ = useMemo(() => monthBoundsUTC(nowMs), [nowMs]);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void fetchUsageRecords(activeWorkspaceId, {
      start_ms: window_.period_start_ms,
      end_ms: window_.period_end_ms,
    })
      .then((rows) => {
        if (cancelled) return;
        setRecords(rows);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load usage");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId, window_.period_start_ms, window_.period_end_ms]);

  if (wsLoading) {
    return (
      <p
        className="p-6 text-sm text-muted-foreground"
        data-testid="costs-loading"
      >
        Loading costs…
      </p>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Costs" />;
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <SectionDegraded
          title="Cost evidence"
          description="Workspace usage and cost evidence could not load from the control plane."
          evidence={error}
        />
      </main>
    );
  }
  if (records === null) {
    return (
      <p
        className="p-6 text-sm text-muted-foreground"
        data-testid="costs-loading"
      >
        Loading costs…
      </p>
    );
  }
  return (
    <CostPageClient
      records={records}
      workspace_id={activeWorkspaceId}
      now_ms={nowMs}
    />
  );
}

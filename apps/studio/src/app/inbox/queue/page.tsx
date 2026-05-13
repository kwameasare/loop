"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { InboxQueue } from "@/components/inbox/inbox-queue";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import { listInbox, type InboxItem } from "@/lib/inbox";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function InboxQueuePage(): JSX.Element {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="container mx-auto p-6">
            <p className="text-sm text-muted-foreground">
              Loading inbox queue...
            </p>
          </main>
        }
      >
        <InboxQueuePageBody />
      </Suspense>
    </RequireAuth>
  );
}

function InboxQueuePageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const searchParams = useSearchParams();
  const focusedAgentId = searchParams.get("agent_id") ?? undefined;
  const activeWorkspaceId = active?.id;
  const [items, setItems] = useState<InboxItem[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setError(null);
    setWorkspaceId(activeWorkspaceId);
    void listInbox(activeWorkspaceId)
      .then((result) => {
        if (cancelled) return;
        setItems(result.items);
        setError(result.degraded_reason ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setItems([]);
        setError(err instanceof Error ? err.message : "Could not load queue");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  const teams = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.team_id))].filter(Boolean);
    return ids.map((id) => ({ id, name: id.replace(/^team-/, "") }));
  }, [items]);
  const agents = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.agent_id))].filter(
      Boolean,
    );
    return ids.map((id) => ({ id, name: id.slice(0, 8) }));
  }, [items]);

  if (wsLoading) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground">Loading inbox queue...</p>
      </main>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Inbox Queue" />;
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <SectionDegraded
          title="Inbox Queue"
          description="The operator queue is unavailable. Studio will not show a false empty queue when the HITL backend route is missing."
          evidence={error}
        />
      </main>
    );
  }

  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Inbox queue</h1>
        <p className="text-muted-foreground text-sm">
          Cross-team queue. Filter by team, agent, or channel and click into any
          conversation to take it over.
        </p>
      </header>
      <InboxQueue
        agents={agents}
        initialAgentId={focusedAgentId}
        items={items}
        now_ms={Date.now()}
        teams={teams}
        workspace_id={workspaceId}
      />
    </main>
  );
}

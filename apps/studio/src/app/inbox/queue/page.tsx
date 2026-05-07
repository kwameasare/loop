"use client";

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { InboxQueue } from "@/components/inbox/inbox-queue";
import {
  FIXTURE_AGENTS,
  FIXTURE_NOW_MS,
  FIXTURE_QUEUE,
  FIXTURE_TEAMS,
  FIXTURE_WORKSPACE_ID,
  listInbox,
  type InboxItem,
} from "@/lib/inbox";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function InboxQueuePage(): JSX.Element {
  return (
    <RequireAuth>
      <InboxQueuePageBody />
    </RequireAuth>
  );
}

function InboxQueuePageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [items, setItems] = useState<InboxItem[]>(FIXTURE_QUEUE);
  const [workspaceId, setWorkspaceId] = useState(FIXTURE_WORKSPACE_ID);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    setWorkspaceId(active.id);
    void listInbox(active.id)
      .then((result) => {
        if (cancelled) return;
        setItems(result.items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (
          err instanceof Error &&
          /LOOP_CP_API_BASE_URL is required/.test(err.message)
        ) {
          setItems(FIXTURE_QUEUE);
          setWorkspaceId(FIXTURE_WORKSPACE_ID);
          return;
        }
        setError(err instanceof Error ? err.message : "Could not load queue");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const teams = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.team_id))].filter(Boolean);
    return ids.length > 0
      ? ids.map((id) => ({ id, name: id.replace(/^team-/, "") }))
      : FIXTURE_TEAMS;
  }, [items]);
  const agents = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.agent_id))].filter(Boolean);
    return ids.length > 0
      ? ids.map((id) => ({ id, name: id.slice(0, 8) }))
      : FIXTURE_AGENTS;
  }, [items]);

  if (wsLoading || !active) {
    return (
      <main className="container mx-auto p-6">
        <p className="text-sm text-muted-foreground">Loading inbox queue...</p>
      </main>
    );
  }

  return (
    <main className="container mx-auto p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Inbox queue</h1>
        <p className="text-muted-foreground text-sm">
          Cross-team queue. Filter by team, agent, or channel and click into
          any conversation to take it over.
        </p>
        {error ? (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </header>
      <InboxQueue
        agents={agents}
        items={items}
        now_ms={Date.now() || FIXTURE_NOW_MS}
        teams={teams}
        workspace_id={workspaceId}
      />
    </main>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { InboxQueue } from "@/components/inbox/inbox-queue";
import {
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
  const [items, setItems] = useState<InboxItem[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
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
        setItems([]);
        setError(err instanceof Error ? err.message : "Could not load queue");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const teams = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.team_id))].filter(Boolean);
    return ids.map((id) => ({ id, name: id.replace(/^team-/, "") }));
  }, [items]);
  const agents = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.agent_id))].filter(Boolean);
    return ids.map((id) => ({ id, name: id.slice(0, 8) }));
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
        now_ms={Date.now()}
        teams={teams}
        workspace_id={workspaceId}
      />
    </main>
  );
}

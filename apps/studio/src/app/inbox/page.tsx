"use client";

/**
 * P0.3: ``/inbox`` — operator escalation queue.
 *
 * Wires the InboxScreen to live cp-api calls for queue load, claim,
 * release, and resolution. The screen still keeps optimistic local
 * feedback, then reconciles each action against the server response.
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/auth/require-auth";
import { InboxScreen } from "@/components/inbox/inbox-screen";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  claimInboxItem,
  listInbox,
  releaseInboxItem,
  resolveInboxItem,
  type InboxItem,
} from "@/lib/inbox";
import { useUser } from "@/lib/use-user";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function InboxPage(): JSX.Element {
  return (
    <RequireAuth>
      <InboxPageBody />
    </RequireAuth>
  );
}

function InboxPageBody(): JSX.Element {
  const { user } = useUser();
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const searchParams = useSearchParams();
  const focusedAgentId = searchParams.get("agent_id") ?? undefined;
  const activeWorkspaceId = active?.id;
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const nowMs = useMemo(() => Date.now(), []);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    void listInbox(activeWorkspaceId)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setError(res.degraded_reason ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load inbox");
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  if (wsLoading) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="inbox-loading">
        Loading inbox…
      </p>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Inbox" />;
  if (!user) {
    return (
      <p className="p-6 text-sm text-muted-foreground">
        Sign in to view the inbox.
      </p>
    );
  }
  if (error) {
    return (
      <main className="container mx-auto p-6">
        <SectionDegraded
          title="Inbox"
          description="The operator inbox is unavailable. Studio will not show an empty queue unless the live queue actually loaded empty."
          evidence={error}
        />
      </main>
    );
  }
  if (items === null) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="inbox-loading">
        Loading inbox…
      </p>
    );
  }

  return (
    <InboxScreen
      initialItems={items}
      workspace_id={activeWorkspaceId}
      operator_id={user.sub}
      now_ms={nowMs}
      focused_agent_id={focusedAgentId}
      onClaimItem={(item) => claimInboxItem(item.id, user.sub)}
      onReleaseItem={(item) => releaseInboxItem(item.id)}
      onResolveItem={(item) => resolveInboxItem(item.id)}
    />
  );
}

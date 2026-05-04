"use client";

/**
 * P0.3: ``/inbox`` — operator escalation queue.
 *
 * Wires the InboxScreen to real cp-api calls. The
 * ``/v1/workspaces/{id}/inbox`` route is not yet mounted on cp (see
 * ``listInbox`` in lib/inbox.ts) so we fall through to an empty queue
 * until that PR lands; the takeover round-trip via
 * ``/v1/conversations/{id}/takeover`` is wired today.
 */

import { useEffect, useMemo, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { InboxScreen } from "@/components/inbox/inbox-screen";
import { listInbox, type InboxItem } from "@/lib/inbox";
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
  const [items, setItems] = useState<InboxItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const nowMs = useMemo(() => Date.now(), []);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void listInbox(active.id)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load inbox");
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active) {
    return (
      <p className="p-6 text-sm text-muted-foreground" data-testid="inbox-loading">
        Loading inbox…
      </p>
    );
  }
  if (!user) {
    return (
      <p className="p-6 text-sm text-muted-foreground">
        Sign in to view the inbox.
      </p>
    );
  }
  if (error) {
    return (
      <p className="p-6 text-sm text-red-600" role="alert">
        {error}
      </p>
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
      workspace_id={active.id}
      operator_id={user.sub}
      now_ms={nowMs}
    />
  );
}

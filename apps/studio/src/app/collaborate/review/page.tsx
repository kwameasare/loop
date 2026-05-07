"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ChangesetApprovals } from "@/components/collaboration/changeset-approvals";
import { PairDebugPanel } from "@/components/collaboration/pair-debug-panel";
import { PresenceBar } from "@/components/collaboration/presence-bar";
import { CommentThreadView } from "@/components/comments/comment-thread";
import {
  fetchCollaborationWorkspace,
  FIXTURE_CHANGESET,
  FIXTURE_PAIR_DEBUG,
  FIXTURE_PRESENCE,
  type CollaborationWorkspace,
} from "@/lib/collaboration";
import { FIXTURE_THREADS } from "@/lib/comments";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

const ME = { id: "u_kojo", display: "Kojo A." };

export default function CollaborateReviewPage(): JSX.Element {
  return (
    <RequireAuth>
      <CollaborateReviewPageBody />
    </RequireAuth>
  );
}

function CollaborateReviewPageBody(): JSX.Element {
  const { active, isLoading: wsLoading } = useActiveWorkspace();
  const [workspace, setWorkspace] = useState<CollaborationWorkspace>({
    presence: FIXTURE_PRESENCE,
    changeset: FIXTURE_CHANGESET,
    pairDebug: FIXTURE_PAIR_DEBUG,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    setError(null);
    void fetchCollaborationWorkspace(active.id)
      .then((next) => {
        if (cancelled) return;
        setWorkspace(next);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load collaboration",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [active]);

  if (wsLoading || !active) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading collaboration workspace...
        </p>
      </main>
    );
  }

  return (
    <main
      data-testid="collaborate-review-page"
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Collaborate · Review
        </p>
        <h1 className="text-2xl font-semibold">Review &amp; pair debug</h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Comments anchor to stable object IDs and survive versions.
          Changesets surface behavior, eval, cost, and latency approvals.
          Pair debugging keeps the trace playhead in sync.
        </p>
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </header>
      <PresenceBar users={workspace.presence} />
      <ChangesetApprovals changeset={workspace.changeset} />
      <div className="grid gap-4 lg:grid-cols-2">
        {FIXTURE_THREADS.map((t) => (
          <CommentThreadView key={t.id} thread={t} currentUser={ME} />
        ))}
      </div>
      <PairDebugPanel session={workspace.pairDebug} />
    </main>
  );
}

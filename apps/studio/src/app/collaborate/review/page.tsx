"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ChangesetApprovals } from "@/components/collaboration/changeset-approvals";
import { PairDebugPanel } from "@/components/collaboration/pair-debug-panel";
import { PresenceBar } from "@/components/collaboration/presence-bar";
import { CommentThreadView } from "@/components/comments/comment-thread";
import {
  SectionDegraded,
  WorkspaceRequiredState,
} from "@/components/section-states";
import {
  EMPTY_PAIR_DEBUG,
  fetchCollaborationWorkspace,
  type CollaborationWorkspace,
} from "@/lib/collaboration";
import type { CommentThread } from "@/lib/comments";
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
    presence: [],
    changeset: null,
    pairDebug: EMPTY_PAIR_DEBUG,
  });
  const [threads] = useState<readonly CommentThread[]>([]);
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

  if (wsLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading collaboration workspace...
        </p>
      </main>
    );
  }
  if (!active) return <WorkspaceRequiredState title="Review" />;

  return (
    <main
      data-testid="collaborate-review-page"
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Collaborate · Review
        </p>
        <h1 className="text-2xl font-semibold">Review &amp; pair debug</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Comments anchor to stable object IDs and survive versions. Changesets
          surface behavior, eval, cost, and latency approvals. Pair debugging
          keeps the trace playhead in sync.
        </p>
      </header>
      {error ? (
        <SectionDegraded
          title="Collaboration evidence"
          description="Presence, changeset, comment, and pair-debug evidence could not load from the control plane."
          evidence={error}
        />
      ) : null}
      <PresenceBar users={workspace.presence} />
      {workspace.changeset ? (
        <ChangesetApprovals changeset={workspace.changeset} />
      ) : (
        <section
          className="rounded-md border bg-card p-4 text-sm text-muted-foreground"
          data-testid="changeset-empty"
        >
          No pending changeset in the live audit window.
        </section>
      )}
      {threads.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {threads.map((t) => (
            <CommentThreadView key={t.id} thread={t} currentUser={ME} />
          ))}
        </div>
      ) : (
        <section
          className="rounded-md border bg-card p-4 text-sm text-muted-foreground"
          data-testid="comments-empty"
        >
          No live comment threads loaded for this workspace.
        </section>
      )}
      <PairDebugPanel session={workspace.pairDebug} />
    </main>
  );
}

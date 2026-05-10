"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import { ChangesetApprovals } from "@/components/collaboration/changeset-approvals";
import { PairDebugAudioControl } from "@/components/collaboration/pair-debug-audio-control";
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
import { fetchCommentThreads, type CommentThread } from "@/lib/comments";
import { useActiveWorkspace } from "@/lib/use-active-workspace";
import { usePresenceSocket } from "@/lib/use-presence-socket";

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
  const activeWorkspaceId = active?.id;
  const [workspace, setWorkspace] = useState<CollaborationWorkspace>({
    presence: [],
    changeset: null,
    pairDebug: EMPTY_PAIR_DEBUG,
  });
  const [threads, setThreads] = useState<readonly CommentThread[]>([]);
  const [error, setError] = useState<string | null>(null);
  const presence = usePresenceSocket({
    workspaceId: activeWorkspaceId,
    callerSub: ME.id,
    display: ME.display,
    focus: workspace.pairDebug.trace[0]?.evidenceRef ?? "collaborate/review",
    initialUsers: workspace.presence,
  });
  const pairDebugParticipants =
    presence.users.length > 0
      ? presence.users
      : workspace.pairDebug.participants;
  const pairDebugSession = {
    ...workspace.pairDebug,
    participants: pairDebugParticipants,
  };
  const teammateCount = pairDebugParticipants.filter(
    (user) => user.id !== ME.id,
  ).length;

  useEffect(() => {
    if (!activeWorkspaceId) return;
    let cancelled = false;
    setError(null);
    setWorkspace({
      presence: [],
      changeset: null,
      pairDebug: EMPTY_PAIR_DEBUG,
    });
    setThreads([]);
    void Promise.allSettled([
      fetchCollaborationWorkspace(activeWorkspaceId),
      fetchCommentThreads(activeWorkspaceId),
    ]).then((results) => {
      if (cancelled) return;
      const [workspaceResult, threadsResult] = results;
      const messages: string[] = [];
      if (workspaceResult.status === "fulfilled") {
        setWorkspace(workspaceResult.value);
      } else {
        messages.push(
          workspaceResult.reason instanceof Error
            ? workspaceResult.reason.message
            : "Could not load collaboration workspace",
        );
      }
      if (threadsResult.status === "fulfilled") {
        setThreads(threadsResult.value.items);
      } else {
        messages.push(
          threadsResult.reason instanceof Error
            ? threadsResult.reason.message
            : "Could not load comment threads",
        );
      }
      if (messages.length > 0) {
        setError(messages.join(" · "));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  if (wsLoading) {
    return (
      <main className="mx-auto max-w-6xl p-6">
        <p className="text-sm text-muted-foreground">
          Loading collaboration workspace...
        </p>
      </main>
    );
  }
  if (!activeWorkspaceId) return <WorkspaceRequiredState title="Review" />;

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
      <section className="grid gap-3 lg:grid-cols-[1fr_auto]">
        <div className="space-y-2">
          <PresenceBar users={pairDebugParticipants} />
          {presence.error ? (
            <p
              className="text-xs text-destructive"
              data-testid="presence-socket-error"
            >
              {presence.error}
            </p>
          ) : null}
          <p
            className="text-xs text-muted-foreground"
            data-testid="presence-socket-state"
          >
            {presence.connected
              ? "Realtime presence connected."
              : "Realtime presence is waiting for cp-api websocket."}
          </p>
        </div>
        {workspace.pairDebug.agentId ? (
          <PairDebugAudioControl
            workspaceId={activeWorkspaceId}
            agentId={workspace.pairDebug.agentId}
            teammateCount={teammateCount}
            participantId={ME.id}
          />
        ) : null}
      </section>
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
            <CommentThreadView
              key={t.id}
              thread={t}
              currentUser={ME}
              {...(t.agentId ? { agentId: t.agentId } : {})}
            />
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
      <PairDebugPanel session={pairDebugSession} />
    </main>
  );
}

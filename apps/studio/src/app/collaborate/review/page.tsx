"use client";

import { ChangesetApprovals } from "@/components/collaboration/changeset-approvals";
import { PairDebugPanel } from "@/components/collaboration/pair-debug-panel";
import { PresenceBar } from "@/components/collaboration/presence-bar";
import { CommentThreadView } from "@/components/comments/comment-thread";
import {
  FIXTURE_CHANGESET,
  FIXTURE_PAIR_DEBUG,
  FIXTURE_PRESENCE,
} from "@/lib/collaboration";
import { FIXTURE_THREADS } from "@/lib/comments";

const ME = { id: "u_kojo", display: "Kojo A." };

export default function CollaborateReviewPage(): JSX.Element {
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
      </header>
      <PresenceBar users={FIXTURE_PRESENCE} />
      <ChangesetApprovals changeset={FIXTURE_CHANGESET} />
      <div className="grid gap-4 lg:grid-cols-2">
        {FIXTURE_THREADS.map((t) => (
          <CommentThreadView key={t.id} thread={t} currentUser={ME} />
        ))}
      </div>
      <PairDebugPanel session={FIXTURE_PAIR_DEBUG} />
    </main>
  );
}

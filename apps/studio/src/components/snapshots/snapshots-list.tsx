"use client";

import { useState } from "react";

import {
  type Snapshot,
  type SnapshotPurpose,
  verifySnapshotSignature,
} from "@/lib/snapshots";

interface SnapshotsListProps {
  snapshots: readonly Snapshot[];
  onBranch?(snap: Snapshot, purpose: SnapshotPurpose): void;
}

const PURPOSE_LABEL: Record<SnapshotPurpose, string> = {
  general: "general",
  audit: "audit",
  incident: "incident",
  demo: "demo",
};

const BRANCH_PURPOSES: readonly SnapshotPurpose[] = [
  "incident",
  "demo",
  "audit",
];

export function SnapshotsList(props: SnapshotsListProps): JSX.Element {
  const { snapshots, onBranch } = props;
  const [branchedFor, setBranchedFor] = useState<
    Record<string, SnapshotPurpose>
  >({});

  if (snapshots.length === 0) {
    return (
      <section
        data-testid="snapshots-empty"
        className="rounded-md border bg-card p-4 text-sm text-muted-foreground"
      >
        No snapshots yet. Pre-promote and post-promote snapshots will appear
        here once available.
      </section>
    );
  }

  return (
    <section
      data-testid="snapshots-list"
      aria-labelledby="snapshots-title"
      className="space-y-3 rounded-md border bg-card p-4"
    >
      <header className="flex items-baseline justify-between">
        <h3 id="snapshots-title" className="text-sm font-semibold">
          Signed snapshots
        </h3>
        <p className="text-xs text-muted-foreground">
          Branchable for incident replay, demo, or audit
        </p>
      </header>
      <ul className="space-y-2">
        {snapshots.map((snap) => {
          const verified = verifySnapshotSignature(snap);
          const branchedPurpose = branchedFor[snap.id];
          return (
            <li
              key={snap.id}
              data-testid={`snapshot-${snap.id}`}
              className="space-y-2 rounded-md border bg-background p-3 text-xs"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="text-sm font-medium">{snap.label}</p>
                <span
                  data-testid={`snapshot-signature-${snap.id}`}
                  className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                    verified
                      ? "border-success/30 bg-success/10 text-success"
                      : "border-destructive/30 bg-destructive/10 text-destructive"
                  }`}
                >
                  {verified ? "signature verified" : "signature failed"}
                </span>
              </div>
              <div className="grid gap-1 text-muted-foreground sm:grid-cols-2">
                <p>
                  <strong className="text-foreground">Taken:</strong>{" "}
                  {snap.takenAt}
                </p>
                <p>
                  <strong className="text-foreground">Purpose:</strong>{" "}
                  {PURPOSE_LABEL[snap.purpose]}
                </p>
                <p className="truncate sm:col-span-2">
                  <strong className="text-foreground">SHA:</strong>{" "}
                  <code className="rounded bg-muted px-1 py-0.5">
                    {snap.sha256}
                  </code>
                </p>
                <p className="truncate sm:col-span-2">
                  <strong className="text-foreground">Signing key:</strong>{" "}
                  <code className="rounded bg-muted px-1 py-0.5">
                    {snap.signingKey}
                  </code>
                </p>
                {snap.branchedFrom ? (
                  <p className="text-muted-foreground sm:col-span-2">
                    Branched from{" "}
                    <code className="rounded bg-muted px-1 py-0.5">
                      {snap.branchedFrom}
                    </code>
                  </p>
                ) : null}
              </div>
              {onBranch && verified ? (
                <div className="flex flex-wrap items-center gap-2">
                  {BRANCH_PURPOSES.map((purpose) => (
                    <button
                      key={purpose}
                      type="button"
                      data-testid={`snapshot-branch-${snap.id}-${purpose}`}
                      onClick={() => {
                        onBranch(snap, purpose);
                        setBranchedFor((prev) => ({
                          ...prev,
                          [snap.id]: purpose,
                        }));
                      }}
                      className="rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted"
                    >
                      Branch for {purpose}
                    </button>
                  ))}
                  {branchedPurpose ? (
                    <span
                      data-testid={`snapshot-branched-${snap.id}`}
                      className="rounded-full border border-success/30 bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success"
                    >
                      Branched for {branchedPurpose}
                    </span>
                  ) : null}
                </div>
              ) : null}
              {!verified ? (
                <p
                  data-testid={`snapshot-blocked-${snap.id}`}
                  className="text-destructive"
                >
                  Branching is blocked until the signature verifies.
                </p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

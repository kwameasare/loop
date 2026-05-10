"use client";

import { useMemo, useState } from "react";

import {
  topLikelyChanges,
  type BehaviorChange,
  type LikelihoodTier,
} from "@/lib/snapshots";

interface WhatCouldBreakProps {
  changes: readonly BehaviorChange[];
  /** Maximum rows to show. Defaults to 5. */
  topK?: number;
  onInspect?(change: BehaviorChange): void;
}

const TIER_LABEL: Record<LikelihoodTier, string> = {
  high: "high likelihood",
  medium: "medium likelihood",
  low: "low likelihood",
};

const TIER_TONE: Record<LikelihoodTier, string> = {
  high: "border-destructive/30 bg-destructive/10 text-destructive",
  medium: "border-warning/30 bg-warning/10 text-warning",
  low: "border-border bg-muted text-muted-foreground",
};

export function WhatCouldBreak(props: WhatCouldBreakProps): JSX.Element {
  const { changes, topK = 5, onInspect } = props;
  const [openId, setOpenId] = useState<string | null>(null);
  const top = useMemo(() => topLikelyChanges(changes, topK), [changes, topK]);

  if (top.length === 0) {
    return (
      <section
        data-testid="what-could-break-empty"
        className="rounded-md border bg-card p-4 text-sm text-muted-foreground"
      >
        No behavior changes detected vs. production. Pre-promote replay still
        recommended.
      </section>
    );
  }

  return (
    <section
      data-testid="what-could-break"
      aria-labelledby="wcb-title"
      className="space-y-3 rounded-md border bg-card p-4"
    >
      <header className="flex items-baseline justify-between">
        <h3 id="wcb-title" className="text-sm font-semibold">
          What could break
        </h3>
        <p className="text-xs text-muted-foreground">
          Top {top.length} likely behavior changes vs. production
        </p>
      </header>
      <ul className="divide-y divide-border" data-testid="wcb-list">
        {top.map((change) => {
          const isOpen = openId === change.id;
          return (
            <li
              key={change.id}
              data-testid={`wcb-row-${change.id}`}
              className="py-2"
            >
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : change.id)}
                aria-expanded={isOpen}
                aria-controls={`wcb-detail-${change.id}`}
                className="flex w-full items-center justify-between gap-3 text-left"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {change.surface}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {change.summary}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-medium ${TIER_TONE[change.likelihood]}`}
                  >
                    {TIER_LABEL[change.likelihood]}
                  </span>
                  <span className="text-xs tabular-nums text-muted-foreground">
                    {change.confidence}%
                  </span>
                </div>
              </button>
              {isOpen ? (
                <div
                  id={`wcb-detail-${change.id}`}
                  data-testid={`wcb-detail-${change.id}`}
                  className="mt-2 space-y-2 rounded-md bg-muted p-3 text-xs"
                >
                  <p>
                    <strong className="text-foreground">Old:</strong>{" "}
                    {change.oldBehavior}
                  </p>
                  <p>
                    <strong className="text-foreground">New:</strong>{" "}
                    {change.newBehavior}
                  </p>
                  <p className="text-muted-foreground">
                    Exemplar transcript:{" "}
                    <code className="rounded bg-background px-1 py-0.5">
                      {change.exemplarTranscriptId}
                    </code>
                    {" · "}
                    Evidence:{" "}
                    <code className="rounded bg-background px-1 py-0.5">
                      {change.evidenceRef}
                    </code>
                  </p>
                  {onInspect ? (
                    <button
                      type="button"
                      data-testid={`wcb-inspect-${change.id}`}
                      onClick={() => onInspect(change)}
                      className="rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted"
                    >
                      Open replay diff
                    </button>
                  ) : null}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

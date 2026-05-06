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
  high: "border-rose-200 bg-rose-50 text-rose-700",
  medium: "border-amber-200 bg-amber-50 text-amber-700",
  low: "border-slate-200 bg-slate-50 text-slate-600",
};

export function WhatCouldBreak(props: WhatCouldBreakProps): JSX.Element {
  const { changes, topK = 5, onInspect } = props;
  const [openId, setOpenId] = useState<string | null>(null);
  const top = useMemo(() => topLikelyChanges(changes, topK), [changes, topK]);

  if (top.length === 0) {
    return (
      <section
        data-testid="what-could-break-empty"
        className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600"
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
      className="rounded-md border border-slate-200 bg-white p-4 space-y-3"
    >
      <header className="flex items-baseline justify-between">
        <h3 id="wcb-title" className="text-sm font-semibold">
          What could break
        </h3>
        <p className="text-xs text-slate-500">
          Top {top.length} likely behavior changes vs. production
        </p>
      </header>
      <ul className="divide-y divide-slate-100" data-testid="wcb-list">
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
                  <p className="truncate text-xs text-slate-500">
                    {change.summary}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={`rounded-full border px-2 py-0.5 text-xs font-medium ${TIER_TONE[change.likelihood]}`}
                  >
                    {TIER_LABEL[change.likelihood]}
                  </span>
                  <span className="text-xs tabular-nums text-slate-500">
                    {change.confidence}%
                  </span>
                </div>
              </button>
              {isOpen ? (
                <div
                  id={`wcb-detail-${change.id}`}
                  data-testid={`wcb-detail-${change.id}`}
                  className="mt-2 space-y-2 rounded-md bg-slate-50 p-3 text-xs"
                >
                  <p>
                    <strong className="text-slate-700">Old:</strong>{" "}
                    {change.oldBehavior}
                  </p>
                  <p>
                    <strong className="text-slate-700">New:</strong>{" "}
                    {change.newBehavior}
                  </p>
                  <p className="text-slate-500">
                    Exemplar transcript:{" "}
                    <code className="rounded bg-white px-1 py-0.5">
                      {change.exemplarTranscriptId}
                    </code>
                    {" · "}
                    Evidence:{" "}
                    <code className="rounded bg-white px-1 py-0.5">
                      {change.evidenceRef}
                    </code>
                  </p>
                  {onInspect ? (
                    <button
                      type="button"
                      data-testid={`wcb-inspect-${change.id}`}
                      onClick={() => onInspect(change)}
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium hover:bg-slate-50"
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

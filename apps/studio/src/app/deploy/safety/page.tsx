"use client";

import { RegressionBisect } from "@/components/deploy/regression-bisect/regression-bisect";
import { WhatCouldBreak } from "@/components/deploy/what-could-break/what-could-break";
import { SnapshotsList } from "@/components/snapshots/snapshots-list";
import {
  FIXTURE_BEHAVIOR_CHANGES,
  FIXTURE_BISECT,
  FIXTURE_SNAPSHOTS,
} from "@/lib/snapshots";

export default function DeploySafetyPage(): JSX.Element {
  return (
    <main
      data-testid="deploy-safety-page"
      className="mx-auto max-w-6xl space-y-8 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ship · Time-travel safety
        </p>
        <h1 className="text-2xl font-semibold">Pre-promote safety</h1>
        <p className="max-w-3xl text-sm text-slate-600">
          See top likely behavior changes from production, jump to old/new
          replay diffs, locate the culprit commit by bisect, and branch signed
          snapshots for incident, demo, or audit replay.
        </p>
      </header>
      <WhatCouldBreak changes={FIXTURE_BEHAVIOR_CHANGES} />
      <RegressionBisect result={FIXTURE_BISECT} />
      <SnapshotsList snapshots={FIXTURE_SNAPSHOTS} />
    </main>
  );
}

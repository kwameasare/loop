"use client";

import { CoBuilderPanel } from "@/components/ai-cobuilder/co-builder-panel";
import { RubberDuck } from "@/components/ai-cobuilder/rubber-duck";
import { SecondPairOfEyes } from "@/components/ai-cobuilder/second-pair-of-eyes";
import {
  FIXTURE_ACTION_DRIVE,
  FIXTURE_ACTION_SUGGEST,
  FIXTURE_OPERATOR,
  FIXTURE_REVIEW,
  FIXTURE_RUBBER_DUCK,
} from "@/lib/ai-cobuilder";

export default function CoBuilderPage(): JSX.Element {
  return (
    <main
      data-testid="cobuilder-page"
      className="mx-auto max-w-6xl space-y-6 p-6"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          AI Co-Builder
        </p>
        <h1 className="text-2xl font-semibold">Suggest, Edit, Drive</h1>
        <p className="max-w-3xl text-sm text-slate-600">
          Every action declares its mode, exact diff, provenance, and budget.
          Apply is gated until consent passes. Rubber Duck explains failing
          traces; Second Pair of Eyes runs adversarial review.
        </p>
      </header>

      <section className="grid gap-4 lg:grid-cols-2">
        <CoBuilderPanel
          action={FIXTURE_ACTION_SUGGEST}
          operator={FIXTURE_OPERATOR}
          selectionContext="agents/refunds-bot/flow/escalate.ts:14"
        />
        <CoBuilderPanel
          action={FIXTURE_ACTION_DRIVE}
          operator={FIXTURE_OPERATOR}
          selectionContext="agents/refunds-bot/kb/index.json"
        />
      </section>

      <RubberDuck diagnosis={FIXTURE_RUBBER_DUCK} />
      <SecondPairOfEyes review={FIXTURE_REVIEW} />
    </main>
  );
}

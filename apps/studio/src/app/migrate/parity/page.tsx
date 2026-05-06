"use client";

import { CutoverPanel } from "@/components/migration/cutover-panel";
import { ParityHarness } from "@/components/migration/parity-harness";
import {
  FIXTURE_BOTPRESS_CUTOVER,
  FIXTURE_BOTPRESS_DIFFS,
  FIXTURE_BOTPRESS_LINEAGE,
  FIXTURE_BOTPRESS_READINESS,
  FIXTURE_BOTPRESS_REPAIRS,
  FIXTURE_BOTPRESS_REPLAY,
} from "@/lib/botpress-import";

export default function MigrationParityPage(): JSX.Element {
  return (
    <main
      data-testid="migration-parity-page"
      className="mx-auto max-w-6xl p-6 space-y-8"
    >
      <header className="space-y-1 border-b pb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Migrate · Parity & cutover
        </p>
        <h1 className="text-2xl font-semibold">
          Botpress parity workspace
        </h1>
        <p className="text-sm text-slate-600 max-w-3xl">
          Lineage stays attached to every diff and repair. Cutover only runs
          after shadow agreement, and rollback triggers stay armed throughout.
        </p>
      </header>
      <ParityHarness
        lineage={FIXTURE_BOTPRESS_LINEAGE}
        readiness={FIXTURE_BOTPRESS_READINESS}
        diffs={FIXTURE_BOTPRESS_DIFFS}
        replay={FIXTURE_BOTPRESS_REPLAY}
        repairs={FIXTURE_BOTPRESS_REPAIRS}
      />
      <CutoverPanel plan={FIXTURE_BOTPRESS_CUTOVER} />
    </main>
  );
}

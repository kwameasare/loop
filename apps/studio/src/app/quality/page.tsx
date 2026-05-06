"use client";

/**
 * UX407 — Target UX quality bar dashboard.
 *
 * Internal review screen tracking Clarity, Control, Precision,
 * Friendliness, Enterprise Readiness, Craft, and Delight per Studio
 * surface. Each failing category links to canonical-standard evidence.
 *
 * Backed by `SAMPLE_QUALITY_REPORTS` until the review pipeline writes
 * to the control plane.
 */

import { useState } from "react";

import { QualityDashboard, ScreenChecklist } from "@/components/quality";
import { SAMPLE_QUALITY_REPORTS, type ScreenQualityReport } from "@/lib/quality";

export default function QualityPage(): JSX.Element {
  const [selected, setSelected] = useState<ScreenQualityReport | null>(null);
  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6" aria-label="Quality bar">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[3fr_4fr]">
        <QualityDashboard
          reports={SAMPLE_QUALITY_REPORTS}
          onSelect={setSelected}
        />
        <div>
          {selected ? (
            <ScreenChecklist key={selected.screen} initial={selected} />
          ) : (
            <p
              role="status"
              className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
            >
              Select a screen to open its checklist. Failing categories link
              back to the target-standard evidence (§37).
            </p>
          )}
        </div>
      </div>
    </main>
  );
}

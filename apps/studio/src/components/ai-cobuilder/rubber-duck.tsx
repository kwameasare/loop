"use client";

import type { RubberDuckDiagnosis } from "@/lib/ai-cobuilder";

interface RubberDuckProps {
  diagnosis: RubberDuckDiagnosis;
}

export function RubberDuck({ diagnosis }: RubberDuckProps): JSX.Element {
  return (
    <section
      data-testid={`rubber-duck-${diagnosis.caseId}`}
      className="space-y-3 rounded-md border border-warning/40 bg-warning/10 p-4"
    >
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-warning">
          Rubber Duck · {diagnosis.caseId}
        </p>
        <p
          data-testid={`rubber-duck-summary-${diagnosis.caseId}`}
          className="mt-1 text-sm font-semibold text-foreground"
        >
          {diagnosis.failureSummary}
        </p>
      </header>

      <ol
        data-testid={`rubber-duck-steps-${diagnosis.caseId}`}
        className="space-y-1 text-xs text-foreground"
      >
        {diagnosis.findings.map((f, i) => (
          <li
            key={f.evidenceRef}
            data-testid={`rubber-duck-step-${i + 1}`}
            className="rounded border bg-background px-2 py-1"
          >
            <span className="font-mono text-[11px] text-muted-foreground">
              {f.step}
            </span>
            <span className="ml-2 text-foreground">{f.observation}</span>
          </li>
        ))}
      </ol>

      <div
        data-testid={`rubber-duck-fix-${diagnosis.caseId}`}
        className="rounded border border-success/40 bg-success/10 p-2"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wider text-success">
          Proposed fix · {diagnosis.proposedFix.mode}
        </p>
        <p className="text-xs font-semibold text-foreground">
          {diagnosis.proposedFix.title}
        </p>
        <p className="text-[11px] text-muted-foreground">
          {diagnosis.proposedFix.rationale}
        </p>
      </div>
    </section>
  );
}

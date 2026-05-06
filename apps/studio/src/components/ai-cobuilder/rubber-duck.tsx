"use client";

import type { RubberDuckDiagnosis } from "@/lib/ai-cobuilder";

interface RubberDuckProps {
  diagnosis: RubberDuckDiagnosis;
}

export function RubberDuck({ diagnosis }: RubberDuckProps): JSX.Element {
  return (
    <section
      data-testid={`rubber-duck-${diagnosis.caseId}`}
      className="space-y-3 rounded-md border border-amber-200 bg-amber-50/50 p-4"
    >
      <header>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-700">
          Rubber Duck · {diagnosis.caseId}
        </p>
        <p
          data-testid={`rubber-duck-summary-${diagnosis.caseId}`}
          className="mt-1 text-sm font-semibold text-slate-900"
        >
          {diagnosis.failureSummary}
        </p>
      </header>

      <ol
        data-testid={`rubber-duck-steps-${diagnosis.caseId}`}
        className="space-y-1 text-xs text-slate-700"
      >
        {diagnosis.findings.map((f, i) => (
          <li
            key={f.evidenceRef}
            data-testid={`rubber-duck-step-${i + 1}`}
            className="rounded border border-slate-200 bg-white px-2 py-1"
          >
            <span className="font-mono text-[11px] text-slate-500">
              {f.step}
            </span>
            <span className="ml-2 text-slate-700">{f.observation}</span>
          </li>
        ))}
      </ol>

      <div
        data-testid={`rubber-duck-fix-${diagnosis.caseId}`}
        className="rounded border border-emerald-300 bg-emerald-50 p-2"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">
          Proposed fix · {diagnosis.proposedFix.mode}
        </p>
        <p className="text-xs font-semibold text-slate-900">
          {diagnosis.proposedFix.title}
        </p>
        <p className="text-[11px] text-slate-600">
          {diagnosis.proposedFix.rationale}
        </p>
      </div>
    </section>
  );
}

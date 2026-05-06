"use client";

import { useMemo, useState } from "react";

import {
  type CoBuilderAction,
  type ConsentEvaluation,
  type OperatorContext,
  applyAction,
  evaluateConsent,
} from "@/lib/ai-cobuilder";

interface CoBuilderPanelProps {
  action: CoBuilderAction;
  operator: OperatorContext;
  selectionContext: string;
  onApply?: (actionId: string, appliedAt: string) => void;
}

const MODE_LABEL: Record<string, string> = {
  suggest: "Suggest",
  edit: "Edit",
  drive: "Drive",
};

export function CoBuilderPanel({
  action,
  operator,
  selectionContext,
  onApply,
}: CoBuilderPanelProps): JSX.Element {
  const evaluation: ConsentEvaluation = useMemo(
    () => evaluateConsent(action, operator),
    [action, operator],
  );
  const [error, setError] = useState<string | null>(null);
  const [appliedAt, setAppliedAt] = useState<string | null>(null);

  function handleApply(): void {
    setError(null);
    try {
      const result = applyAction(action, operator);
      setAppliedAt(result.appliedAt);
      onApply?.(action.id, result.appliedAt);
    } catch (e) {
      setError(e instanceof Error ? e.message : "apply failed");
    }
  }

  return (
    <section
      data-testid={`cobuilder-${action.id}`}
      className="space-y-3 rounded-md border border-slate-200 bg-white p-4 shadow-sm"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p
            data-testid={`cobuilder-mode-${action.id}`}
            className="inline-block rounded-full border border-slate-300 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600"
          >
            {MODE_LABEL[action.mode] ?? action.mode}
          </p>
          <h3 className="mt-1 text-sm font-semibold text-slate-900">
            {action.title}
          </h3>
        </div>
        <p
          data-testid={`cobuilder-budget-${action.id}`}
          className="text-right text-xs text-slate-500"
        >
          ${action.cost.usd.toFixed(2)} · {action.cost.latencyMs}ms
        </p>
      </header>

      <p
        data-testid={`cobuilder-selection-${action.id}`}
        className="rounded bg-slate-50 px-2 py-1 text-xs text-slate-600"
      >
        Selection: <span className="font-mono">{selectionContext}</span>
      </p>

      <p className="text-xs text-slate-700">{action.rationale}</p>

      <pre
        data-testid={`cobuilder-diff-${action.id}`}
        className="overflow-auto rounded bg-slate-900 px-3 py-2 text-[11px] leading-snug text-slate-100"
      >
        <span className="block text-slate-400">--- {action.diff.path}</span>
        {action.diff.body}
      </pre>

      <div data-testid={`cobuilder-provenance-${action.id}`} className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Provenance
        </p>
        <ul className="space-y-1 text-xs text-slate-600">
          {action.provenance.map((p) => (
            <li
              key={p.evidenceRef}
              data-testid={`cobuilder-provenance-row-${p.evidenceRef}`}
              className="rounded border border-slate-200 px-2 py-1"
            >
              <span className="font-medium text-slate-800">{p.source}</span>
              <span className="ml-1 text-slate-500">— {p.excerpt}</span>
            </li>
          ))}
        </ul>
      </div>

      {action.requiredScopes.length > 0 ? (
        <p
          data-testid={`cobuilder-scopes-${action.id}`}
          className="text-[11px] text-slate-500"
        >
          Requires: {action.requiredScopes.join(", ")}
        </p>
      ) : null}

      {!evaluation.ok ? (
        <ul
          data-testid={`cobuilder-blocked-${action.id}`}
          className="space-y-1 rounded border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900"
        >
          {evaluation.reasons.map((r) => (
            <li key={r.code}>
              <span className="font-semibold uppercase">{r.code}:</span>{" "}
              {r.message}
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p
          data-testid={`cobuilder-error-${action.id}`}
          className="rounded border border-rose-300 bg-rose-50 px-2 py-1 text-xs text-rose-900"
        >
          {error}
        </p>
      ) : null}

      {appliedAt ? (
        <p
          data-testid={`cobuilder-applied-${action.id}`}
          className="rounded border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs text-emerald-900"
        >
          Applied at {appliedAt}.
        </p>
      ) : (
        <button
          type="button"
          data-testid={`cobuilder-apply-${action.id}`}
          onClick={handleApply}
          disabled={!evaluation.ok}
          className="rounded bg-slate-900 px-3 py-1 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          Apply ({MODE_LABEL[action.mode] ?? action.mode})
        </button>
      )}
    </section>
  );
}

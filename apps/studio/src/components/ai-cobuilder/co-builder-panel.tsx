"use client";

import { useMemo, useState } from "react";

import {
  type ApplyResult,
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
  onApplyAction?: (action: CoBuilderAction) => Promise<ApplyResult> | ApplyResult;
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
  onApplyAction,
  onApply,
}: CoBuilderPanelProps): JSX.Element {
  const evaluation: ConsentEvaluation = useMemo(
    () => evaluateConsent(action, operator),
    [action, operator],
  );
  const [error, setError] = useState<string | null>(null);
  const [appliedAt, setAppliedAt] = useState<string | null>(null);
  const [appliedEvidenceRef, setAppliedEvidenceRef] = useState<string | null>(null);
  const [changeSetId, setChangeSetId] = useState<string | null>(null);
  const [nextUrl, setNextUrl] = useState<string | null>(null);
  const [isApplying, setIsApplying] = useState(false);

  async function handleApply(): Promise<void> {
    setError(null);
    setIsApplying(true);
    try {
      const result = onApplyAction
        ? await onApplyAction(action)
        : applyAction(action, operator);
      setAppliedAt(result.appliedAt);
      setAppliedEvidenceRef(result.evidenceRef);
      setChangeSetId(result.changeSet?.id ?? null);
      setNextUrl(result.nextUrl ?? null);
      onApply?.(action.id, result.appliedAt);
    } catch (e) {
      setError(e instanceof Error ? e.message : "apply failed");
    } finally {
      setIsApplying(false);
    }
  }

  return (
    <section
      data-testid={`cobuilder-${action.id}`}
      className="space-y-3 instrument-panel rounded-2xl p-4 shadow-sm"
    >
      <header className="flex items-start justify-between gap-3">
        <div>
          <p
            data-testid={`cobuilder-mode-${action.id}`}
            className="inline-block rounded-full border bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            {MODE_LABEL[action.mode] ?? action.mode}
          </p>
          <h3 className="mt-1 text-sm font-semibold text-foreground">
            {action.title}
          </h3>
        </div>
        <p
          data-testid={`cobuilder-budget-${action.id}`}
          className="text-right text-xs text-muted-foreground"
        >
          ${action.cost.usd.toFixed(2)} · {action.cost.latencyMs}ms
        </p>
      </header>

      <p
        data-testid={`cobuilder-selection-${action.id}`}
        className="rounded bg-muted px-2 py-1 text-xs text-muted-foreground"
      >
        Selection: <span className="font-mono">{selectionContext}</span>
      </p>

      <p className="text-xs text-foreground">{action.rationale}</p>

      <pre
        data-testid={`cobuilder-diff-${action.id}`}
        className="overflow-auto rounded bg-foreground/95 px-3 py-2 text-[11px] leading-snug text-background"
      >
        <span className="block text-background/70">--- {action.diff.path}</span>
        {action.diff.body}
      </pre>

      <div data-testid={`cobuilder-provenance-${action.id}`} className="space-y-1">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Provenance
        </p>
        <ul className="space-y-1 text-xs text-muted-foreground">
          {action.provenance.map((p) => (
            <li
              key={p.evidenceRef}
              data-testid={`cobuilder-provenance-row-${p.evidenceRef}`}
              className="rounded border bg-background px-2 py-1"
            >
              <span className="font-medium text-foreground">{p.source}</span>
              <span className="ml-1 text-muted-foreground">— {p.excerpt}</span>
            </li>
          ))}
        </ul>
      </div>

      {action.requiredScopes.length > 0 ? (
        <p
          data-testid={`cobuilder-scopes-${action.id}`}
          className="text-[11px] text-muted-foreground"
        >
          Requires: {action.requiredScopes.join(", ")}
        </p>
      ) : null}

      {!evaluation.ok ? (
        <ul
          data-testid={`cobuilder-blocked-${action.id}`}
          className="space-y-1 rounded border border-warning/40 bg-warning/10 p-2 text-xs text-warning"
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
          className="rounded border border-destructive/40 bg-destructive/10 px-2 py-1 text-xs text-destructive"
        >
          {error}
        </p>
      ) : null}

      {appliedAt ? (
        <p
          data-testid={`cobuilder-applied-${action.id}`}
          className="rounded border border-success/40 bg-success/10 px-2 py-1 text-xs text-success"
        >
          Applied at {appliedAt}.{" "}
          {changeSetId ? (
            <span data-testid={`cobuilder-changeset-${action.id}`}>
              Change set {changeSetId}.
            </span>
          ) : null}{" "}
          {appliedEvidenceRef ? (
            <span data-testid={`cobuilder-evidence-${action.id}`}>
              Evidence {appliedEvidenceRef}.
            </span>
          ) : null}{" "}
          {nextUrl ? (
            <a className="font-medium underline" href={nextUrl}>
              Open workflow
            </a>
          ) : null}
        </p>
      ) : (
        <button
          type="button"
          data-testid={`cobuilder-apply-${action.id}`}
          onClick={handleApply}
          disabled={!evaluation.ok || isApplying}
          className="rounded bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isApplying ? "Applying..." : `Apply (${MODE_LABEL[action.mode] ?? action.mode})`}
        </button>
      )}
    </section>
  );
}

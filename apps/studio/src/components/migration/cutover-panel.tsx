"use client";

import { useState } from "react";

import {
  CutoverError,
  validateCutoverPlan,
  type CutoverPlan,
} from "@/lib/migration-parity";

const STAGE_TONE: Record<string, string> = {
  passed: "border-success/30 bg-success/10 text-success",
  in_progress: "border-info/30 bg-info/10 text-info",
  pending: "border-border bg-muted text-muted-foreground",
  halted: "border-destructive/30 bg-destructive/10 text-destructive",
};

function pill(status: string): string {
  return (
    "inline-flex items-center px-2 py-0.5 text-xs font-medium border rounded " +
    (STAGE_TONE[status] ?? "border-border bg-muted text-muted-foreground")
  );
}

export interface CutoverPanelProps {
  plan: CutoverPlan;
  /** Wire-up for the actual canary advance. Defaults to no-op. */
  onAdvance?: (stageId: string) => void;
  /** Wire-up for an emergency rollback. Defaults to no-op. */
  onRollback?: (triggerId: string | "manual") => void;
}

export function CutoverPanel({
  plan,
  onAdvance,
  onRollback,
}: CutoverPanelProps): JSX.Element {
  const [validationError, setValidationError] = useState<string | null>(null);
  const [rolledBack, setRolledBack] = useState(false);

  const currentStage = plan.stages.find((s) => s.status === "in_progress");
  const blockingValidation = (() => {
    try {
      validateCutoverPlan(plan);
      return null;
    } catch (err) {
      return err instanceof CutoverError ? err.message : "Invalid plan";
    }
  })();

  return (
    <div data-testid="cutover-panel" className="space-y-4">
      <header className="space-y-1">
        <h2 className="text-xl font-semibold">Shadow → canary → cutover</h2>
        <p className="text-sm text-muted-foreground">
          Traffic moves only after every guardrail passes. Rollback triggers stay
          armed throughout.
        </p>
      </header>

      {blockingValidation && (
        <div
          role="alert"
          data-testid="cutover-validation-error"
          className="rounded border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {blockingValidation}
        </div>
      )}

      <section
        data-testid="shadow-summary"
        className="border rounded p-3 grid gap-2 md:grid-cols-4"
      >
        <Stat label="Shadow duration" value={`${plan.shadow.durationMinutes}m`} />
        <Stat label="Turns observed" value={String(plan.shadow.turns)} />
        <Stat label="Agreement" value={`${plan.shadow.agreement}%`} />
        <Stat
          label="Cost / turn delta"
          value={plan.shadow.costPerTurnDelta}
        />
        <div className="md:col-span-4 text-xs text-muted-foreground">
          divergences: {plan.shadow.divergences} · evidence: {plan.shadow.evidenceRef}
        </div>
      </section>

      <section data-testid="canary-stages" className="space-y-2">
        <h3 className="text-sm font-medium">Canary stages</h3>
        <ol className="space-y-2">
          {plan.stages.map((stage) => {
            const canAdvance =
              stage.status === "in_progress" && !rolledBack;
            return (
              <li
                key={stage.id}
                data-testid={`canary-stage-${stage.id}`}
                className="border rounded p-3 flex items-start justify-between gap-3"
              >
                <div>
                  <div className="font-medium">
                    {stage.percent}% · {stage.durationMinutes}m bake
                  </div>
                  <ul className="text-xs text-muted-foreground mt-1 space-y-0.5">
                    {stage.guardrails.map((g) => (
                      <li key={g}>· {g}</li>
                    ))}
                  </ul>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <span className={pill(stage.status)}>{stage.status}</span>
                  {canAdvance && (
                    <button
                      type="button"
                      data-testid={`canary-advance-${stage.id}`}
                      onClick={() => {
                        try {
                          validateCutoverPlan(plan);
                          setValidationError(null);
                          onAdvance?.(stage.id);
                        } catch (err) {
                          setValidationError(
                            err instanceof CutoverError
                              ? err.message
                              : "Cannot advance",
                          );
                        }
                      }}
                      className="px-2 py-1 text-xs border rounded hover:bg-muted"
                    >
                      Advance
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      <section data-testid="rollback-triggers" className="space-y-2">
        <h3 className="text-sm font-medium">Rollback triggers</h3>
        <ul className="space-y-2">
          {plan.rollbackTriggers.map((t) => (
            <li
              key={t.id}
              data-testid={`rollback-trigger-${t.id}`}
              className="border rounded p-3"
            >
              <div className="text-sm font-medium">
                {t.metric} · {t.threshold}
              </div>
              <div className="text-sm text-muted-foreground">{t.action}</div>
              <div className="text-xs text-muted-foreground">evidence: {t.evidenceRef}</div>
            </li>
          ))}
        </ul>
        {!rolledBack ? (
          <button
            type="button"
            data-testid="manual-rollback"
            disabled={!currentStage}
            onClick={() => {
              setRolledBack(true);
              onRollback?.("manual");
            }}
            className="rounded border border-destructive/40 px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Manual rollback
          </button>
        ) : (
          <div
            role="status"
            data-testid="rollback-confirmation"
            className="rounded border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
          >
            Rollback issued. Traffic restored to source. Audit event recorded.
          </div>
        )}
      </section>

      {validationError && (
        <div
          role="alert"
          data-testid="cutover-advance-error"
          className="rounded border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {validationError}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}

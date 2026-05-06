"use client";

import { useState } from "react";

import { StageStepper } from "@/components/target";
import {
  IMPORT_WIZARD_STEPS,
  type ImportWizardStepId,
  findWizardStep,
  wizardStepStates,
} from "@/lib/migration";
import { cn } from "@/lib/utils";

export interface ImportWizardProps {
  initialStepId?: ImportWizardStepId;
  className?: string;
  onStepChange?: (id: ImportWizardStepId) => void;
}

/**
 * Guided import wizard (canonical §18.3). Renders the nine canonical steps
 * using the shared StageStepper primitive and surfaces the active step
 * description plus next/previous controls. The step grammar matches the rest
 * of the studio's object-state primitives so this never feels like a one-off.
 */
export function ImportWizard({
  initialStepId = "choose-source",
  className,
  onStepChange,
}: ImportWizardProps) {
  const [currentId, setCurrentId] = useState<ImportWizardStepId>(initialStepId);
  const current = findWizardStep(currentId);
  const steps = wizardStepStates(currentId).map((s) => ({
    id: s.id,
    label: s.label,
    state: s.state,
  }));

  function move(delta: number) {
    const idx = current.index - 1 + delta;
    const next = IMPORT_WIZARD_STEPS[idx];
    if (!next) return;
    setCurrentId(next.id);
    onStepChange?.(next.id);
  }

  const atStart = current.index === 1;
  const atEnd = current.index === IMPORT_WIZARD_STEPS.length;

  return (
    <section
      className={cn("flex flex-col gap-4", className)}
      data-testid="import-wizard"
      aria-labelledby="import-wizard-heading"
    >
      <header className="flex flex-col gap-1">
        <h2 id="import-wizard-heading" className="text-lg font-semibold">
          Import wizard
        </h2>
        <p className="text-sm text-muted-foreground">
          A safety workflow, not a setup wizard. Every step protects secrets,
          mappings, parity, or rollback before it advances.
        </p>
      </header>

      <StageStepper steps={steps} currentId={currentId} />

      <article
        data-testid="import-wizard-step-detail"
        className="rounded-md border border-border bg-card p-4"
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Step {current.index} of {IMPORT_WIZARD_STEPS.length}
        </p>
        <h3 className="mt-1 text-base font-semibold">{current.label}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{current.description}</p>
      </article>

      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => move(-1)}
          disabled={atStart}
          data-testid="import-wizard-back"
          className={cn(
            "rounded-md border px-3 py-1.5 text-sm font-medium",
            atStart
              ? "cursor-not-allowed border-border bg-muted text-muted-foreground"
              : "border-border bg-card hover:bg-muted",
          )}
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => move(1)}
          disabled={atEnd}
          data-testid="import-wizard-next"
          className={cn(
            "rounded-md px-3 py-1.5 text-sm font-medium",
            atEnd
              ? "cursor-not-allowed bg-muted text-muted-foreground"
              : "bg-primary text-primary-foreground hover:bg-primary/90",
          )}
        >
          {atEnd ? "Cutover armed" : "Continue"}
        </button>
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";
import {
  CheckCircle2,
  ListRestart,
  PlayCircle,
  ShieldCheck,
} from "lucide-react";

import { StatePanel } from "@/components/target";
import {
  saveObservedFailureEval,
  type ObservedFailureEvalInput,
  type ObservedFailureEvalResponse,
} from "@/lib/behavior-repair";
import type { BehaviorSentence } from "@/lib/behavior";

export interface FailureRepairLoopPanelProps {
  agentId: string;
  sentence: BehaviorSentence | null;
  saveEval?: (
    agentId: string,
    input: ObservedFailureEvalInput,
  ) => Promise<ObservedFailureEvalResponse>;
}

function evidenceTraceRef(sentence: BehaviorSentence): string {
  const evidenceParts = sentence.telemetry.evidence
    .split(/[\s,]+/)
    .filter(Boolean);
  return (
    evidenceParts.find((part) => part.toLowerCase().includes("trace")) ??
    `trace/${sentence.id}`
  );
}

function inputForSentence(
  sentence: BehaviorSentence,
): ObservedFailureEvalInput {
  const traceRef = evidenceTraceRef(sentence);
  return {
    sentence_id: sentence.id,
    sentence_text: sentence.text,
    trace_id: traceRef,
    failure_reason: `Observed failure against ${sentence.id}: ${sentence.telemetry.contradictedTraces} contradictions and ${sentence.telemetry.neverInvokedTurns} not-invoked turns in sampled telemetry.`,
    expected_outcome: `Future answers satisfy this behavior: ${sentence.text}`,
    proposed_fix: `Tighten the behavior rule and replay nearby production turns for: ${sentence.text}`,
    replay_ref: `replay/${sentence.id}/nearby-turns`,
  };
}

export function FailureRepairLoopPanel({
  agentId,
  sentence,
  saveEval = saveObservedFailureEval,
}: FailureRepairLoopPanelProps) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<ObservedFailureEvalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!sentence) return;
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      const response = await saveEval(agentId, inputForSentence(sentence));
      setSaved(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not save this failure as an eval case.",
      );
    } finally {
      setSaving(false);
    }
  }

  if (!sentence) {
    return (
      <StatePanel
        state="empty"
        title="Select a sentence to repair"
        className="rounded-md border bg-card"
      >
        Select a behavior sentence with observed telemetry before saving a
        regression eval.
      </StatePanel>
    );
  }

  const traceRef = evidenceTraceRef(sentence);

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="failure-repair-loop"
      aria-labelledby="failure-repair-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Repair loop
          </p>
          <h3
            className="mt-1 text-sm font-semibold"
            id="failure-repair-heading"
          >
            Fix this, replay, save the regression
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            The selected sentence becomes a concrete failure, replay reference,
            proposed fix, and eval case in one controlled action.
          </p>
        </div>
        <span className="rounded-md border bg-background px-2 py-1 text-xs font-medium text-muted-foreground">
          90-second loop
        </span>
      </div>

      <ol className="mt-4 space-y-2 text-sm">
        <li className="flex gap-2 rounded-md border bg-background px-3 py-2">
          <CheckCircle2
            className="mt-0.5 h-4 w-4 shrink-0 text-info"
            aria-hidden
          />
          <span>
            <span className="font-medium">Selected failure:</span>{" "}
            {sentence.telemetry.contradictedTraces} contradictions and{" "}
            {sentence.telemetry.neverInvokedTurns} missed invocations.
          </span>
        </li>
        <li className="flex gap-2 rounded-md border bg-background px-3 py-2">
          <PlayCircle
            className="mt-0.5 h-4 w-4 shrink-0 text-info"
            aria-hidden
          />
          <span>
            <span className="font-medium">Replay scope:</span> current trace
            plus nearby turns from <span className="break-all">{traceRef}</span>
            .
          </span>
        </li>
        <li className="flex gap-2 rounded-md border bg-background px-3 py-2">
          <ShieldCheck
            className="mt-0.5 h-4 w-4 shrink-0 text-info"
            aria-hidden
          />
          <span>
            <span className="font-medium">Regression spec:</span> future answers
            must satisfy this sentence before promotion.
          </span>
        </li>
      </ol>

      <button
        type="button"
        className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
        disabled={saving}
        onClick={() => void handleSave()}
        data-testid="failure-repair-save-eval"
      >
        <ListRestart className="h-4 w-4" aria-hidden />
        {saving ? "Saving eval" : "Save failure as eval"}
      </button>

      {saved ? (
        <StatePanel
          className="mt-4"
          state="success"
          title="Regression eval saved"
        >
          <p data-testid="failure-repair-saved">
            Case {saved.case_id} was added to suite {saved.suite_id}.
          </p>
        </StatePanel>
      ) : null}

      {error ? (
        <StatePanel className="mt-4" state="error" title="Eval was not saved">
          {error}
        </StatePanel>
      ) : null}
    </section>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle2,
  ListRestart,
  PlayCircle,
  ShieldCheck,
} from "lucide-react";

import { StatePanel } from "@/components/target";
import {
  requestObservedFailureRepair,
  saveObservedFailureEval,
  type ObservedFailureEvalInput,
  type ObservedFailureEvalResponse,
  type ObservedFailureRepairInput,
  type ObservedFailureRepairResponse,
} from "@/lib/behavior-repair";
import type { BehaviorSentence } from "@/lib/behavior";

export interface FailureRepairLoopPanelProps {
  agentId: string;
  sentence: BehaviorSentence | null;
  autoGenerateKey?: number | undefined;
  autoSaveKey?: number | undefined;
  saveEval?: (
    agentId: string,
    input: ObservedFailureEvalInput,
  ) => Promise<ObservedFailureEvalResponse>;
  requestRepair?: (
    agentId: string,
    input: ObservedFailureRepairInput,
  ) => Promise<ObservedFailureRepairResponse>;
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
    sentence_role: sentence.role,
    trace_id: traceRef,
    failure_reason: `Observed failure against ${sentence.id}: ${sentence.telemetry.contradictedTraces} contradictions and ${sentence.telemetry.neverInvokedTurns} not-invoked turns in sampled telemetry.`,
    expected_outcome: `Future answers satisfy this behavior: ${sentence.text}`,
    proposed_fix: `Tighten the behavior rule and replay nearby production turns for: ${sentence.text}`,
    replay_ref: `replay/${sentence.id}/nearby-turns`,
    risk_tags: sentence.riskIds,
    target_object_kind: targetObjectKind(sentence),
  };
}

function targetObjectKind(sentence: BehaviorSentence): string {
  const text = sentence.text.toLowerCase();
  if (sentence.role === "tool" || text.includes("tool")) return "tool_contract";
  if (sentence.role === "memory" || text.includes("memory")) {
    return "memory_policy";
  }
  if (
    text.includes("knowledge") ||
    text.includes("cite") ||
    text.includes("policy")
  ) {
    return "knowledge_chunk";
  }
  if (
    text.includes("channel") ||
    text.includes("whatsapp") ||
    text.includes("telegram") ||
    text.includes("slack") ||
    text.includes("sms") ||
    text.includes("voice") ||
    text.includes("email")
  ) {
    return "channel_constraint";
  }
  return "behavior_sentence";
}

export function FailureRepairLoopPanel({
  agentId,
  sentence,
  autoGenerateKey,
  autoSaveKey,
  saveEval = saveObservedFailureEval,
  requestRepair = requestObservedFailureRepair,
}: FailureRepairLoopPanelProps) {
  const [proposing, setProposing] = useState(false);
  const [proposal, setProposal] =
    useState<ObservedFailureRepairResponse | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<ObservedFailureEvalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handlePropose = useCallback(async () => {
    if (!sentence) return;
    setProposing(true);
    setProposal(null);
    setSaved(null);
    setError(null);
    try {
      const input = inputForSentence(sentence);
      const repairInput: ObservedFailureRepairInput = {
        sentence_id: input.sentence_id,
        sentence_text: input.sentence_text,
        trace_id: input.trace_id,
        failure_reason: input.failure_reason,
      };
      if (input.replay_ref) repairInput.replay_ref = input.replay_ref;
      if (input.sentence_role) repairInput.sentence_role = input.sentence_role;
      if (input.risk_tags) repairInput.risk_tags = input.risk_tags;
      if (input.target_object_kind) {
        repairInput.target_object_kind = input.target_object_kind;
      }
      const response = await requestRepair(agentId, repairInput);
      setProposal(response);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not generate a focused repair proposal.",
      );
    } finally {
      setProposing(false);
    }
  }, [agentId, requestRepair, sentence]);

  const handleSave = useCallback(async () => {
    if (!sentence) return;
    setSaving(true);
    setSaved(null);
    setError(null);
    try {
      const input = inputForSentence(sentence);
      const evalInput: ObservedFailureEvalInput = {
        ...input,
        expected_outcome: proposal
          ? `Future answers satisfy this behavior after ${proposal.proposal.title}: ${sentence.text}`
          : input.expected_outcome,
        proposed_fix: proposal?.proposal.diff ?? input.proposed_fix,
      };
      const replayRef = proposal?.replay.draft_ref ?? input.replay_ref;
      if (replayRef) evalInput.replay_ref = replayRef;
      const response = await saveEval(agentId, evalInput);
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
  }, [agentId, proposal, saveEval, sentence]);

  useEffect(() => {
    if (!autoGenerateKey) return;
    void handlePropose();
  }, [autoGenerateKey, handlePropose]);

  useEffect(() => {
    if (!autoSaveKey) return;
    void handleSave();
  }, [autoSaveKey, handleSave]);

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
        className="mt-4 inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-60"
        disabled={proposing}
        onClick={() => void handlePropose()}
        data-testid="failure-repair-generate"
      >
        <PlayCircle className="h-4 w-4" aria-hidden />
        {proposing ? "Generating fix" : "Generate focused fix"}
      </button>

      {proposal ? (
        <div
          className="mt-4 rounded-md border bg-muted/30 p-3 text-xs"
          data-testid="failure-repair-proposal"
        >
          <p className="font-semibold">{proposal.proposal.title}</p>
          <p className="mt-1 text-muted-foreground">{proposal.proposal.diff}</p>
          <dl className="mt-3 grid gap-2 sm:grid-cols-4">
            <div>
              <dt className="font-medium">Improved</dt>
              <dd>{proposal.replay.improved}</dd>
            </div>
            <div>
              <dt className="font-medium">Unchanged</dt>
              <dd>{proposal.replay.unchanged}</dd>
            </div>
            <div>
              <dt className="font-medium">Regressed</dt>
              <dd>{proposal.replay.regressed}</dd>
            </div>
            <div>
              <dt className="font-medium">Needs review</dt>
              <dd>{proposal.replay.needs_review}</dd>
            </div>
          </dl>
          <p className="mt-2 text-muted-foreground">
            Evidence: {proposal.evidence_refs.join(", ")}
          </p>
        </div>
      ) : null}

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

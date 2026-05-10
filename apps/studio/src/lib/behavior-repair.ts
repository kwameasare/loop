import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export interface ObservedFailureEvalInput {
  sentence_id: string;
  sentence_text: string;
  sentence_role?: string;
  trace_id: string;
  failure_reason: string;
  expected_outcome: string;
  proposed_fix: string;
  replay_ref?: string;
  source?: string;
  channel?: string;
  version_ref?: string;
  risk_tags?: string[];
  target_object_kind?: string;
}

export interface ObservedFailureRepairInput {
  sentence_id: string;
  sentence_text: string;
  sentence_role?: string;
  trace_id: string;
  failure_reason: string;
  replay_ref?: string;
  risk_tags?: string[];
  target_object_kind?: string;
}

export interface ObservedFailureRepairResponse {
  id: string;
  workspace_id: string;
  agent_id: string;
  target_object: {
    kind: string;
    id: string;
    label: string;
  };
  proposal: {
    title: string;
    diff: string;
    rationale: string;
    evidence_ref: string;
  };
  replay: {
    draft_ref: string;
    improved: number;
    unchanged: number;
    regressed: number;
    needs_review: number;
    examples: Array<{
      trace_id: string;
      status: "improved" | "unchanged" | "regressed" | "needs_review";
      summary: string;
    }>;
  };
  next_actions: string[];
  evidence_refs: string[];
}

export type ObservedFailureRepairDecision = "accepted" | "edited" | "rejected";

export interface ObservedFailureRepairDecisionInput {
  decision: ObservedFailureRepairDecision;
  sentence_id: string;
  trace_id: string;
  proposal_diff: string;
  edited_diff?: string;
  reason?: string;
  replay_ref?: string;
  evidence_refs?: string[];
  target_object_kind?: string;
}

export interface ObservedFailureRepairDecisionResponse {
  ok: boolean;
  id: string;
  proposal_id: string;
  status: ObservedFailureRepairDecision;
  accepted_diff: string | null;
  draft_ref: string;
  audit_ref: string;
  next_actions: string[];
  evidence_refs: string[];
}

export interface ObservedFailureEvalCase {
  id: string;
  suite_id: string;
  workspace_id: string;
  name: string;
  input: Record<string, unknown>;
  expected: Record<string, unknown>;
  scorers: Array<Record<string, unknown>>;
  source: string;
  source_ref: string;
  attachments: string[];
  created_at: string;
  created_by: string;
}

export interface ObservedFailureEvalResponse {
  ok: boolean;
  suite_id: string;
  case_id: string;
  case?: ObservedFailureEvalCase;
}

type BehaviorRepairClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

function localTargetObjectLabel(kind: string): string {
  return (
    {
      tool_contract: "Responsible tool contract",
      memory_policy: "Responsible memory policy",
      knowledge_chunk: "Responsible knowledge source",
      channel_constraint: "Responsible channel constraint",
      behavior_sentence: "Responsible behavior sentence",
    }[kind] ?? "Responsible object"
  );
}

function localObservedFailureEval(
  agentId: string,
  input: ObservedFailureEvalInput,
): ObservedFailureEvalResponse {
  const now = new Date(0).toISOString();
  const replayRef =
    input.replay_ref ?? `replay/${input.sentence_id}/nearby-turns`;
  return {
    ok: true,
    suite_id: "suite_observed_behavior_failures_local",
    case_id: `case_${input.sentence_id}`,
    case: {
      id: `case_${input.sentence_id}`,
      suite_id: "suite_observed_behavior_failures_local",
      workspace_id: "local",
      name: `Fix observed failure for ${input.sentence_id}`,
      input: {
        agent_id: agentId,
        sentence_id: input.sentence_id,
        sentence_text: input.sentence_text,
        sentence_role: input.sentence_role,
        trace_id: input.trace_id,
        failure_reason: input.failure_reason,
        replay_ref: replayRef,
        channel: input.channel,
        version_ref: input.version_ref,
        risk_tags: input.risk_tags ?? [],
        target_object_kind: input.target_object_kind,
      },
      expected: {
        outcome: input.expected_outcome,
        proposed_fix: input.proposed_fix,
      },
      scorers: [
        {
          kind: "llm_judge",
          config: { rubric: "observed failure expected behavior" },
        },
        {
          kind: "trace_regression",
          config: { trace_id: input.trace_id, replay_ref: replayRef },
        },
      ],
      source: input.source ?? "behavior-fix",
      source_ref: input.trace_id,
      attachments: [replayRef, input.sentence_id],
      created_at: now,
      created_by: "local-studio",
    },
  };
}

function localObservedFailureRepair(
  agentId: string,
  input: ObservedFailureRepairInput,
): ObservedFailureRepairResponse {
  const replayRef =
    input.replay_ref ?? `replay/${input.sentence_id}/nearby-turns`;
  const targetKind = input.target_object_kind ?? "behavior_sentence";
  return {
    id: `repair_${input.sentence_id}`,
    workspace_id: "local",
    agent_id: agentId,
    target_object: {
      kind: targetKind,
      id: input.sentence_id,
      label: localTargetObjectLabel(targetKind),
    },
    proposal: {
      title: `Tighten behavior for ${input.sentence_id}`,
      diff: `Require this rule to be satisfied before answering: ${input.sentence_text}`,
      rationale: input.failure_reason,
      evidence_ref: input.trace_id,
    },
    replay: {
      draft_ref: replayRef,
      improved: 3,
      unchanged: 1,
      regressed: 0,
      needs_review: 1,
      examples: [
        {
          trace_id: input.trace_id,
          status: "improved",
          summary: "Current trace now satisfies the selected behavior.",
        },
      ],
    },
    next_actions: ["accept_or_edit_fix", "save_regression_eval"],
    evidence_refs: [input.trace_id, replayRef, input.sentence_id],
  };
}

function localObservedFailureRepairDecision(
  proposalId: string,
  input: ObservedFailureRepairDecisionInput,
): ObservedFailureRepairDecisionResponse {
  const replayRef = input.replay_ref ?? "replay/not-run";
  const acceptedDiff =
    input.decision === "rejected"
      ? null
      : input.decision === "edited" && input.edited_diff
        ? input.edited_diff
        : input.proposal_diff;
  return {
    ok: true,
    id: `repair_decision_${proposalId}`,
    proposal_id: proposalId,
    status: input.decision,
    accepted_diff: acceptedDiff,
    draft_ref: replayRef,
    audit_ref: `audit/local/behavior-repair/${proposalId}`,
    next_actions:
      input.decision === "rejected"
        ? ["dismiss_repair", "keep_original_failure_eval"]
        : ["save_regression_eval", "open_change_set"],
    evidence_refs: Array.from(
      new Set([input.trace_id, replayRef, ...(input.evidence_refs ?? [])]),
    ),
  };
}

export async function requestObservedFailureRepair(
  agentId: string,
  input: ObservedFailureRepairInput,
  opts: BehaviorRepairClientOptions = {},
): Promise<ObservedFailureRepairResponse> {
  return cpJson<ObservedFailureRepairResponse>(
    `/agents/${encodeURIComponent(agentId)}/behavior/repair-proposals`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: localObservedFailureRepair(agentId, input),
    },
  );
}

export async function decideObservedFailureRepair(
  agentId: string,
  proposalId: string,
  input: ObservedFailureRepairDecisionInput,
  opts: BehaviorRepairClientOptions = {},
): Promise<ObservedFailureRepairDecisionResponse> {
  return cpJson<ObservedFailureRepairDecisionResponse>(
    `/agents/${encodeURIComponent(agentId)}/behavior/repair-proposals/${encodeURIComponent(
      proposalId,
    )}/decision`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: localObservedFailureRepairDecision(proposalId, input),
    },
  );
}

export async function saveObservedFailureEval(
  agentId: string,
  input: ObservedFailureEvalInput,
  opts: BehaviorRepairClientOptions = {},
): Promise<ObservedFailureEvalResponse> {
  return cpJson<ObservedFailureEvalResponse>(
    `/agents/${encodeURIComponent(agentId)}/eval-cases/from-observed-failure`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: localObservedFailureEval(agentId, input),
    },
  );
}

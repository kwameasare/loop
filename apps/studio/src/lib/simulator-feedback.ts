import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type FirstProofRating = "good" | "bad" | "risky" | "unclear";

export interface SimulatorTurnRatingInput {
  rating: FirstProofRating;
  prompt: string;
  final_answer: string;
  channel: string;
  trace_id: string;
  issue_annotation: string;
  save_as_eval: boolean;
  cost_usd: number;
  latency_ms: number;
}

export interface SimulatorTurnRatingRecord {
  id: string;
  workspace_id: string;
  agent_id: string;
  rating: FirstProofRating;
  prompt: string;
  final_answer: string;
  channel: string;
  trace_id: string;
  issue_annotation: string;
  candidate_artifact: {
    kind: string;
    title: string;
    expected_outcome: string;
    source: string;
    trace_id: string;
  };
  eval_case_ref: null | {
    suite_id: string;
    case_id: string;
    case?: Record<string, unknown>;
  };
  behavior_note_ref: null | {
    id: string;
    kind: "risk_rule" | "clarification_prompt";
    status: string;
    title: string;
    body: string;
    rating: FirstProofRating;
    evidence_ref: string;
  };
  cost_usd: number;
  latency_ms: number;
  created_by: string;
  created_at: string;
}

function localRating(
  agentId: string,
  input: SimulatorTurnRatingInput,
): SimulatorTurnRatingRecord {
  const title =
    input.rating === "good"
      ? "Preserve this behavior"
      : input.rating === "bad"
        ? "Prevent this failure from recurring"
        : input.rating === "risky"
          ? "Add a risk rule or escalation"
          : "Clarify this ambiguous behavior";
  const kind =
    input.rating === "good"
      ? "positive_eval_or_few_shot"
      : input.rating === "bad"
        ? "regression_eval_candidate"
        : input.rating === "risky"
          ? "risk_rule_candidate"
          : "clarification_note_candidate";
  return {
    id: `simrate_${input.rating}`,
    workspace_id: "local",
    agent_id: agentId,
    ...input,
    candidate_artifact: {
      kind,
      title,
      expected_outcome:
        input.issue_annotation ||
        input.final_answer ||
        "Preserve the expected outcome.",
      source: "first_proof",
      trace_id: input.trace_id || "trace/not-captured",
    },
    eval_case_ref: input.save_as_eval
      ? {
          suite_id: "suite_first_proof",
          case_id: `case_${input.rating}`,
        }
      : null,
    behavior_note_ref:
      input.rating === "risky" || input.rating === "unclear"
        ? {
            id: `bnote_${input.rating}`,
            kind:
              input.rating === "risky" ? "risk_rule" : "clarification_prompt",
            status: "candidate",
            title,
            body:
              input.issue_annotation ||
              "Convert this first-proof finding into behavior structure.",
            rating: input.rating,
            evidence_ref: input.trace_id || `simulator-turn/${input.rating}`,
          }
        : null,
    created_by: "local",
    created_at: new Date(0).toISOString(),
  };
}

export async function rateSimulatorTurn(
  agentId: string,
  input: SimulatorTurnRatingInput,
  opts: UxWireupClientOptions = {},
): Promise<SimulatorTurnRatingRecord> {
  return cpJson<SimulatorTurnRatingRecord>(
    `/agents/${encodeURIComponent(agentId)}/simulator/turn-ratings`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: localRating(agentId, input),
    },
  );
}

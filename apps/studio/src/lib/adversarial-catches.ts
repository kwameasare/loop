import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type AdversarialRiskClass = "low" | "medium" | "high";
export type AdversarialCatchStatus = "open" | "resolved" | "dismissed";

export interface AdversarialProbeRunInput {
  rule_id: string;
  rule_text: string;
  risk_class?: AdversarialRiskClass;
  budget_tokens?: number;
}

export interface AdversarialProbeBudgets {
  workspace_id: string;
  budgets: Record<AdversarialRiskClass, number>;
  updated_by: string;
  updated_at: string;
}

export type AdversarialProbeBudgetUpdate = Partial<
  Record<AdversarialRiskClass, number>
>;

export interface AdversarialProbeRunRecord {
  id: string;
  workspace_id: string;
  agent_id: string;
  rule_id: string;
  risk_class: AdversarialRiskClass;
  budget_tokens: number;
  budget_tokens_used: number;
  status: "completed" | "budget_exhausted";
  created_by: string;
  created_at: string;
}

export interface AdversarialCatchEvalRef {
  suite_id: string;
  case_id: string;
}

export interface AdversarialCatchResolution {
  intended_interpretation: string;
  rejected_interpretation: string;
  proposed_patch: string;
  dismiss_reason: string;
  created_by: string;
  created_at: string;
}

export interface AdversarialCatch {
  id: string;
  workspace_id: string;
  agent_id: string;
  probe_run_id: string;
  rule_id: string;
  rule_text: string;
  question: string;
  generated_scenario: string;
  evidence_ref: string;
  risk_class: AdversarialRiskClass;
  status: AdversarialCatchStatus;
  resolution: AdversarialCatchResolution | null;
  eval_case_refs: AdversarialCatchEvalRef[];
  created_at: string;
  updated_at: string;
}

export interface AdversarialProbeRunResponse {
  run: AdversarialProbeRunRecord;
  catches: AdversarialCatch[];
}

export interface CatchResolutionInput {
  intended_interpretation?: string;
  rejected_interpretation?: string;
  proposed_patch?: string;
  dismiss_reason?: string;
  create_eval_cases?: boolean;
}

export interface ListAdversarialCatchesResponse {
  items: AdversarialCatch[];
}

type AdversarialCatchesClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

function localQuestionFor(ruleText: string): {
  question: string;
  generated_scenario: string;
} {
  const lowered = ruleText.toLowerCase();
  if (lowered.includes("refund") && lowered.includes("500")) {
    return {
      question:
        'You said "never approve refunds over $500." This generated conversation would approve $555 across two refund calls. Should this cap apply per refund call or cumulatively per conversation?',
      generated_scenario:
        "User requests two refunds of $275 and $280 in the same conversation.",
    };
  }
  if (lowered.includes("never")) {
    return {
      question:
        "This rule uses `never`. Should the prohibition apply absolutely, or are there named escalation exceptions?",
      generated_scenario: `Generated user asks for an exception to: ${ruleText.slice(
        0,
        160,
      )}`,
    };
  }
  if (lowered.includes("always")) {
    return {
      question:
        "This rule uses `always`. Should the agent follow it even when tool, memory, channel, or compliance evidence conflicts?",
      generated_scenario: `Generated user combines the rule with conflicting policy evidence: ${ruleText.slice(
        0,
        160,
      )}`,
    };
  }
  return {
    question:
      "This rule has more than one plausible interpretation. Which one should the agent preserve in future evals?",
    generated_scenario: `Generated paraphrase probes ambiguity in: ${ruleText.slice(
      0,
      160,
    )}`,
  };
}

function localProbeRun(
  agentId: string,
  input: AdversarialProbeRunInput,
): AdversarialProbeRunResponse {
  const now = new Date(0).toISOString();
  const runId = `probe_${input.rule_id.replace(/[^a-z0-9_]/gi, "_")}`;
  const question = localQuestionFor(input.rule_text);
  return {
    run: {
      id: runId,
      workspace_id: "local",
      agent_id: agentId,
      rule_id: input.rule_id,
      risk_class: input.risk_class ?? "medium",
      budget_tokens: input.budget_tokens ?? 2000,
      budget_tokens_used: Math.min(input.budget_tokens ?? 2000, 640),
      status: "completed",
      created_by: "local-studio",
      created_at: now,
    },
    catches: [
      {
        id: `catch_${input.rule_id.replace(/[^a-z0-9_]/gi, "_")}`,
        workspace_id: "local",
        agent_id: agentId,
        probe_run_id: runId,
        rule_id: input.rule_id,
        rule_text: input.rule_text,
        question: question.question,
        generated_scenario: question.generated_scenario,
        evidence_ref: `adversarial_probe/${runId}/${input.rule_id}`,
        risk_class: input.risk_class ?? "medium",
        status: "open",
        resolution: null,
        eval_case_refs: [],
        created_at: now,
        updated_at: now,
      },
    ],
  };
}

function localResolvedCatch(
  agentId: string,
  catchId: string,
  input: CatchResolutionInput,
): AdversarialCatch {
  const now = new Date(0).toISOString();
  const dismissed = Boolean(input.dismiss_reason?.trim());
  return {
    id: catchId,
    workspace_id: "local",
    agent_id: agentId,
    probe_run_id: "probe_local",
    rule_id: "local_rule",
    rule_text: "Local fallback rule",
    question: "Local fallback catch was resolved.",
    generated_scenario: "Local fallback scenario.",
    evidence_ref: `adversarial_probe/probe_local/${catchId}`,
    risk_class: "medium",
    status: dismissed ? "dismissed" : "resolved",
    resolution: {
      intended_interpretation: input.intended_interpretation ?? "",
      rejected_interpretation: input.rejected_interpretation ?? "",
      proposed_patch: input.proposed_patch ?? "",
      dismiss_reason: input.dismiss_reason ?? "",
      created_by: "local-studio",
      created_at: now,
    },
    eval_case_refs:
      input.create_eval_cases === false || dismissed
        ? []
        : [
            {
              suite_id: "suite_adversarial_catches_local",
              case_id: `case_${catchId}_accepted`,
            },
            {
              suite_id: "suite_adversarial_catches_local",
              case_id: `case_${catchId}_rejected`,
            },
          ],
    created_at: now,
    updated_at: now,
  };
}

export async function runAdversarialProbe(
  agentId: string,
  input: AdversarialProbeRunInput,
  opts: AdversarialCatchesClientOptions = {},
): Promise<AdversarialProbeRunResponse> {
  return cpJson<AdversarialProbeRunResponse>(
    `/agents/${encodeURIComponent(agentId)}/adversarial-probes/run`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: localProbeRun(agentId, input),
    },
  );
}

export async function getAdversarialProbeBudgets(
  workspaceId: string,
  opts: AdversarialCatchesClientOptions = {},
): Promise<AdversarialProbeBudgets> {
  return cpJson<AdversarialProbeBudgets>(
    `/workspaces/${encodeURIComponent(workspaceId)}/adversarial-probe-budgets`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: {
        workspace_id: workspaceId,
        budgets: { low: 1000, medium: 2000, high: 4000 },
        updated_by: "local-studio",
        updated_at: new Date(0).toISOString(),
      },
    },
  );
}

export async function updateAdversarialProbeBudgets(
  workspaceId: string,
  input: AdversarialProbeBudgetUpdate,
  opts: AdversarialCatchesClientOptions = {},
): Promise<AdversarialProbeBudgets> {
  return cpJson<AdversarialProbeBudgets>(
    `/workspaces/${encodeURIComponent(workspaceId)}/adversarial-probe-budgets`,
    {
      ...opts,
      method: "PATCH",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        workspace_id: workspaceId,
        budgets: {
          low: input.low ?? 1000,
          medium: input.medium ?? 2000,
          high: input.high ?? 4000,
        },
        updated_by: "local-studio",
        updated_at: new Date(0).toISOString(),
      },
    },
  );
}

export async function listAdversarialCatches(
  agentId: string,
  opts: AdversarialCatchesClientOptions = {},
): Promise<ListAdversarialCatchesResponse> {
  return cpJson<ListAdversarialCatchesResponse>(
    `/agents/${encodeURIComponent(agentId)}/catches`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: { items: [] },
    },
  );
}

export async function resolveAdversarialCatch(
  agentId: string,
  catchId: string,
  input: CatchResolutionInput,
  opts: AdversarialCatchesClientOptions = {},
): Promise<AdversarialCatch> {
  return cpJson<AdversarialCatch>(
    `/agents/${encodeURIComponent(agentId)}/catches/${encodeURIComponent(
      catchId,
    )}/resolve`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: localResolvedCatch(agentId, catchId, input),
    },
  );
}

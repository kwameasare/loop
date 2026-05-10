import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type BranchStatus = "active" | "staged" | "merged" | "abandoned";
export type ChangeSetStatus =
  | "draft"
  | "ready_for_tests"
  | "ready_for_review"
  | "converted_to_release_candidate"
  | "abandoned";
export type ReleaseCandidateStatus =
  | "draft"
  | "testing"
  | "blocked"
  | "ready_for_approval"
  | "approved"
  | "deployable"
  | "superseded";
export type GateStatus = "pending" | "passed" | "failed";

export interface AgentBranch {
  id: string;
  agent_id: string;
  name: string;
  base_version_id: string;
  created_by_user_id: string;
  status: BranchStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentChangeSet {
  id: string;
  agent_id: string;
  branch_id: string;
  name: string;
  summary: string;
  source_type: string;
  source_refs: string[];
  changed_objects: Array<Record<string, unknown>>;
  status: ChangeSetStatus;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  eval_results_ref: string | null;
  required_eval_suites: string[];
}

export interface ReleaseCandidateGate {
  id: string;
  label: string;
  status: GateStatus;
  evidence_ref: string | null;
  message: string;
}

export interface ReleaseCandidateApproval {
  id: string;
  state: string;
  satisfied: boolean;
  comment: string;
  decided_at: string | null;
  actor_sub?: string;
}

export interface AgentReleaseCandidate {
  id: string;
  agent_id: string;
  branch_id: string;
  change_set_id: string;
  candidate_version_id: string;
  readiness: ReleaseCandidateGate[];
  required_eval_suites: string[];
  required_approvals: ReleaseCandidateApproval[];
  status: ReleaseCandidateStatus;
  created_at: string;
  updated_at: string;
}

export interface AgentWorkflow {
  branches: AgentBranch[];
  change_sets: AgentChangeSet[];
  release_candidates: AgentReleaseCandidate[];
}

type AgentWorkflowClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

type ChangeSetClientOptions = AgentWorkflowClientOptions & {
  fallbackChangeSet?: AgentChangeSet;
};

type ReleaseCandidateClientOptions = AgentWorkflowClientOptions & {
  fallbackReleaseCandidate?: AgentReleaseCandidate;
};

const LOCAL_NOW = new Date(0).toISOString();

export function localAgentWorkflow(agentId: string): AgentWorkflow {
  return {
    branches: [
      {
        id: "br_local_refund",
        agent_id: agentId,
        name: "draft/refund-policy-fix",
        base_version_id: "production",
        created_by_user_id: "local-builder",
        status: "active",
        created_at: LOCAL_NOW,
        updated_at: LOCAL_NOW,
      },
    ],
    change_sets: [
      {
        id: "cs_local_refund",
        agent_id: agentId,
        branch_id: "br_local_refund",
        name: "Use current refund policy",
        summary:
          "Collected behavior and eval changes for current refund-policy citations.",
        source_type: "failed_eval",
        source_refs: ["eval/refund/current-policy"],
        changed_objects: [
          {
            type: "behavior",
            id: "behavior.refund_policy",
            summary: "Cite May 2026 policy before refund window.",
          },
        ],
        status: "ready_for_review",
        created_by_user_id: "local-builder",
        created_at: LOCAL_NOW,
        updated_at: LOCAL_NOW,
        eval_results_ref: "eval/run/refund-core/green",
        required_eval_suites: ["refund-core"],
      },
    ],
    release_candidates: [
      {
        id: "rc_local_refund",
        agent_id: agentId,
        branch_id: "br_local_refund",
        change_set_id: "cs_local_refund",
        candidate_version_id: "ver_local_refund",
        readiness: [
          {
            id: "eval:refund-core",
            label: "Eval suite refund-core",
            status: "passed",
            evidence_ref: "eval/run/refund-core/green",
            message:
              "Required eval suite passed before release candidate creation.",
          },
        ],
        required_eval_suites: ["refund-core"],
        required_approvals: [
          {
            id: "owner",
            state: "requested",
            satisfied: false,
            comment: "",
            decided_at: null,
          },
          {
            id: "compliance",
            state: "requested",
            satisfied: false,
            comment: "",
            decided_at: null,
          },
        ],
        status: "ready_for_approval",
        created_at: LOCAL_NOW,
        updated_at: LOCAL_NOW,
      },
    ],
  };
}

export async function listAgentWorkflow(
  agentId: string,
  opts: AgentWorkflowClientOptions = {},
): Promise<AgentWorkflow> {
  return cpJson<AgentWorkflow>(
    `/agents/${encodeURIComponent(agentId)}/workflow`,
    {
      ...opts,
      fallback:
        opts.allowFixture === true
          ? localAgentWorkflow(agentId)
          : { branches: [], change_sets: [], release_candidates: [] },
    },
  );
}

export async function createAgentBranch(
  agentId: string,
  input: { name: string; base_version_id?: string },
  opts: AgentWorkflowClientOptions = {},
): Promise<AgentBranch> {
  const fallback = {
    ...localAgentWorkflow(agentId).branches[0]!,
    ...input,
    id: `br_local_${Date.now()}`,
    status: "active" as const,
    updated_at: new Date().toISOString(),
  };
  return cpJson<AgentBranch>(
    `/agents/${encodeURIComponent(agentId)}/branches`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback,
    },
  );
}

export async function createAgentChangeSet(
  agentId: string,
  input: {
    branch_id: string;
    name: string;
    summary?: string;
    source_type?: string;
    source_refs?: string[];
    changed_objects?: Array<Record<string, unknown>>;
  },
  opts: AgentWorkflowClientOptions = {},
): Promise<AgentChangeSet> {
  const fallback = {
    ...localAgentWorkflow(agentId).change_sets[0]!,
    ...input,
    id: `cs_local_${Date.now()}`,
    status: "draft" as const,
    updated_at: new Date().toISOString(),
    eval_results_ref: null,
    required_eval_suites: [],
  };
  return cpJson<AgentChangeSet>(
    `/agents/${encodeURIComponent(agentId)}/change-sets`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback,
    },
  );
}

export async function markChangeSetReadyForTests(
  agentId: string,
  changeSetId: string,
  opts: ChangeSetClientOptions = {},
): Promise<AgentChangeSet> {
  return cpJson<AgentChangeSet>(
    `/agents/${encodeURIComponent(agentId)}/change-sets/${encodeURIComponent(
      changeSetId,
    )}/ready-for-tests`,
    {
      ...opts,
      method: "POST",
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...(opts.fallbackChangeSet ??
          localAgentWorkflow(agentId).change_sets[0]!),
        status: "ready_for_tests",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function markChangeSetReadyForReview(
  agentId: string,
  changeSetId: string,
  input: {
    eval_results_ref: string;
    required_eval_suites?: string[];
    passed?: boolean;
  },
  opts: ChangeSetClientOptions = {},
): Promise<AgentChangeSet> {
  return cpJson<AgentChangeSet>(
    `/agents/${encodeURIComponent(agentId)}/change-sets/${encodeURIComponent(
      changeSetId,
    )}/ready-for-review`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...(opts.fallbackChangeSet ??
          localAgentWorkflow(agentId).change_sets[0]!),
        status: "ready_for_review",
        eval_results_ref: input.eval_results_ref,
        required_eval_suites: input.required_eval_suites ?? ["refund-core"],
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function createReleaseCandidate(
  agentId: string,
  changeSetId: string,
  input: { required_eval_suites?: string[]; required_approvals?: string[] },
  opts: AgentWorkflowClientOptions = {},
): Promise<AgentReleaseCandidate> {
  return cpJson<AgentReleaseCandidate>(
    `/agents/${encodeURIComponent(agentId)}/change-sets/${encodeURIComponent(
      changeSetId,
    )}/release-candidates`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localAgentWorkflow(agentId).release_candidates[0]!,
        id: `rc_local_${Date.now()}`,
        change_set_id: changeSetId,
        required_eval_suites: input.required_eval_suites ?? ["refund-core"],
        status: "ready_for_approval",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function approveReleaseCandidate(
  agentId: string,
  releaseCandidateId: string,
  input: { approval_id: string; comment?: string },
  opts: ReleaseCandidateClientOptions = {},
): Promise<AgentReleaseCandidate> {
  const base =
    opts.fallbackReleaseCandidate ??
    localAgentWorkflow(agentId).release_candidates[0]!;
  const approvals = base.required_approvals.map((approval) =>
    approval.id === input.approval_id
      ? {
          ...approval,
          state: "approved",
          satisfied: true,
          comment: input.comment ?? "",
          decided_at: new Date().toISOString(),
        }
      : approval,
  );
  return cpJson<AgentReleaseCandidate>(
    `/agents/${encodeURIComponent(
      agentId,
    )}/release-candidates/${encodeURIComponent(releaseCandidateId)}/approve`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...base,
        required_approvals: approvals,
        status: approvals.every((approval) => approval.satisfied)
          ? "deployable"
          : "approved",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type ChangePackageStatus =
  | "draft"
  | "generated"
  | "submitted"
  | "approved"
  | "deployable"
  | "deployed"
  | "changes_requested"
  | "stale"
  | "revoked";

export interface ChangePackageGenerateInput {
  branch_id?: string;
  change_set_id?: string;
  release_candidate_id?: string;
  from_version_id?: string;
  to_version_id?: string;
  target_environment?: string;
  summary?: string;
  semantic_diff?: Array<Record<string, unknown>>;
  eval_results_ref?: string;
  replay_results_ref?: string;
  risk_summary?: string;
  cost_summary?: string;
  latency_summary?: string;
  channel_readiness_summary?: string;
  tool_changes?: Array<Record<string, unknown>>;
  memory_changes?: Array<Record<string, unknown>>;
  knowledge_changes?: Array<Record<string, unknown>>;
  rollback_target_version_id?: string;
}

export interface ChangePackageApproval {
  id: string;
  role: string;
  required: boolean;
  satisfied: boolean;
  reason: string;
  state?: string;
  actor_sub?: string;
  decided_at?: string;
  content_hash?: string;
  comment?: string;
  invalidated_at?: string;
  invalidated_reason?: string;
}

export interface PreApprovedClassUse {
  id: string;
  workspace_id?: string;
  agent_id?: string;
  granted_by_user_id?: string;
  granted_to_user_id?: string;
  team_id?: string;
  allowed_change_types: string[];
  excluded_change_types: string[];
  risk_ceiling: "low" | "medium" | "high";
  expires_at: string;
  status: string;
  reason?: string;
  matched_change_types?: string[];
  matched_risk?: string;
}

export type ChangePackageApprovalDecision =
  | "approve"
  | "reject"
  | "request_changes"
  | "revoke";

export interface ChangePackageApprovalInput {
  approval_id: string;
  decision: ChangePackageApprovalDecision;
  comment?: string;
}

export interface ChangePackageApprovalOptions extends UxWireupClientOptions {
  fallbackPackage?: ChangePackage;
}

export interface ChangePackage {
  id: string;
  workspace_id: string;
  agent_id: string;
  branch_id: string;
  from_version_id: string;
  to_version_id: string;
  commitment_document_id: string;
  commitment_document_version: number;
  summary: string;
  semantic_diff: Array<Record<string, unknown>>;
  eval_results_ref: string;
  replay_results_ref: string;
  risk_summary: string;
  cost_summary: string;
  latency_summary: string;
  channel_readiness_summary: string;
  tool_changes: Array<Record<string, unknown>>;
  memory_changes: Array<Record<string, unknown>>;
  knowledge_changes: Array<Record<string, unknown>>;
  required_approvals: ChangePackageApproval[];
  pre_approved_classes: PreApprovedClassUse[];
  approval_status: string;
  rollback_target_version_id: string;
  evidence_pack_id: string;
  evidence: Record<string, string>;
  content_hash: string;
  status: ChangePackageStatus;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  stale_at: string | null;
}

export interface CurrentChangePackageResponse {
  item: ChangePackage | null;
}

export function buildLocalChangePackage(agentId: string): ChangePackage {
  return {
    id: "change_package_unconfigured",
    workspace_id: "",
    agent_id: agentId,
    branch_id: "main/draft",
    from_version_id: "production",
    to_version_id: "draft",
    commitment_document_id: "commitment_unconfigured",
    commitment_document_version: 0,
    summary: "No preflight Change Package has been generated for this agent.",
    semantic_diff: [],
    eval_results_ref: "evals/not-run",
    replay_results_ref: "replay/not-run",
    risk_summary: "Generate preflight before requesting approval.",
    cost_summary: "No cost estimate yet.",
    latency_summary: "No latency estimate yet.",
    channel_readiness_summary: "No channel readiness summary yet.",
    tool_changes: [],
    memory_changes: [],
    knowledge_changes: [],
    required_approvals: [],
    pre_approved_classes: [],
    approval_status: "not_requested",
    rollback_target_version_id: "none",
    evidence_pack_id: "evidence_pack_unconfigured",
    evidence: {},
    content_hash: "unconfigured",
    status: "draft",
    created_at: "",
    updated_at: "",
    submitted_at: null,
    stale_at: null,
  };
}

export async function fetchCurrentChangePackage(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<CurrentChangePackageResponse> {
  return cpJson<CurrentChangePackageResponse>(
    `/agents/${encodeURIComponent(agentId)}/change-packages/current`,
    {
      ...opts,
      fallback: { item: null },
    },
  );
}

export async function generateChangePackage(
  agentId: string,
  input: ChangePackageGenerateInput,
  opts: UxWireupClientOptions = {},
): Promise<ChangePackage> {
  return cpJson<ChangePackage>(
    `/agents/${encodeURIComponent(agentId)}/change-packages/preflight`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        ...buildLocalChangePackage(agentId),
        ...input,
        status: "generated",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function submitChangePackage(
  agentId: string,
  packageId: string,
  opts: UxWireupClientOptions = {},
): Promise<ChangePackage> {
  return cpJson<ChangePackage>(
    `/agents/${encodeURIComponent(agentId)}/change-packages/${encodeURIComponent(
      packageId,
    )}/submit`,
    {
      ...opts,
      method: "POST",
      fallback: {
        ...buildLocalChangePackage(agentId),
        id: packageId,
        status: "submitted",
        submitted_at: new Date().toISOString(),
      },
    },
  );
}

export async function recordChangePackageApproval(
  agentId: string,
  packageId: string,
  input: ChangePackageApprovalInput,
  opts: ChangePackageApprovalOptions = {},
): Promise<ChangePackage> {
  return cpJson<ChangePackage>(
    `/agents/${encodeURIComponent(agentId)}/change-packages/${encodeURIComponent(
      packageId,
    )}/approvals`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: applyLocalApproval(
        opts.fallbackPackage ?? buildLocalChangePackage(agentId),
        packageId,
        input,
      ),
    },
  );
}

export function applyLocalApproval(
  changePackage: ChangePackage,
  packageId: string,
  input: ChangePackageApprovalInput,
): ChangePackage {
  const now = new Date().toISOString();
  const approvals = changePackage.required_approvals.map((approval) => {
    if (approval.id !== input.approval_id) return approval;
    if (input.decision === "approve") {
      return {
        ...approval,
        satisfied: true,
        state: "approved",
        decided_at: now,
        content_hash: changePackage.content_hash,
        comment: input.comment ?? "",
      };
    }
    return {
      ...approval,
      satisfied: false,
      state: input.decision,
      decided_at: now,
      content_hash: changePackage.content_hash,
      comment: input.comment ?? "",
    };
  });
  const required = approvals.filter((approval) => approval.required);
  const approved = required.filter((approval) => approval.satisfied);
  const approval_status =
    input.decision === "approve"
      ? approved.length === required.length
        ? "approved"
        : approved.length
          ? "partially_approved"
          : "blocked"
      : input.decision;
  const status =
    approval_status === "approved"
      ? "approved"
      : input.decision === "approve"
        ? "submitted"
        : input.decision === "revoke"
          ? "revoked"
          : "changes_requested";
  return {
    ...changePackage,
    id: packageId,
    required_approvals: approvals,
    approval_status,
    status,
    updated_at: now,
  };
}

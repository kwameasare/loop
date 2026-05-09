import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type MemoryPolicyScope =
  | "turn"
  | "conversation"
  | "session"
  | "user"
  | "workspace";

export type MemoryPolicyApprovalStatus =
  | "draft"
  | "review_required"
  | "approved"
  | "blocked";

export interface MemoryPolicy {
  id: string;
  workspace_id: string;
  agent_id: string;
  scope: MemoryPolicyScope;
  allowed_memory_types: string[];
  retention: string;
  consent_requirement: string;
  pii_policy: string;
  delete_behavior: string;
  privacy_implications: string[];
  source_trace_required: boolean;
  approval_status: MemoryPolicyApprovalStatus;
  content_hash: string;
  approval_invalidated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryPoliciesResponse {
  items: MemoryPolicy[];
}

export type MemoryPolicyInput = Pick<
  MemoryPolicy,
  | "scope"
  | "allowed_memory_types"
  | "retention"
  | "consent_requirement"
  | "pii_policy"
  | "delete_behavior"
  | "privacy_implications"
  | "source_trace_required"
>;

const LOCAL_NOW = new Date(0).toISOString();

export function localMemoryPolicies(agentId: string): MemoryPolicy[] {
  return [
    {
      id: "mp_local_session",
      workspace_id: "local",
      agent_id: agentId,
      scope: "session",
      allowed_memory_types: ["scratchpad", "conversation_state"],
      retention: "Expires with the active conversation session.",
      consent_requirement: "Covered by channel session disclosure.",
      pii_policy: "PII is kept transient and never promoted to durable memory.",
      delete_behavior: "Session expiry deletes the memory automatically.",
      privacy_implications: [
        "Used only to keep the current task coherent.",
        "Never affects another conversation.",
      ],
      source_trace_required: true,
      approval_status: "draft",
      content_hash: "local_session_policy",
      approval_invalidated_at: null,
      created_at: LOCAL_NOW,
      updated_at: LOCAL_NOW,
    },
    {
      id: "mp_local_user",
      workspace_id: "local",
      agent_id: agentId,
      scope: "user",
      allowed_memory_types: ["preference", "support_context"],
      retention: "Keep confirmed user preferences for 365 days.",
      consent_requirement: "Explicit consent required before durable write.",
      pii_policy:
        "Do not store secrets, payment data, or unconfirmed identifiers.",
      delete_behavior: "Delete on user request with audit trail.",
      privacy_implications: [
        "Durable preference affects future conversations for this user.",
        "Every write must link to the source turn and writer version.",
      ],
      source_trace_required: true,
      approval_status: "review_required",
      content_hash: "local_user_policy",
      approval_invalidated_at: null,
      created_at: LOCAL_NOW,
      updated_at: LOCAL_NOW,
    },
    {
      id: "mp_local_workspace",
      workspace_id: "local",
      agent_id: agentId,
      scope: "workspace",
      allowed_memory_types: ["team_preference", "operational_exception"],
      retention: "Requires compliance review before any workspace-wide write.",
      consent_requirement: "Admin approval and tenant notice required.",
      pii_policy: "Workspace memory cannot store user-level PII.",
      delete_behavior: "Delete through governance request with audit trail.",
      privacy_implications: [
        "Workspace memory can affect every user in the tenant.",
        "Policy changes must appear in deployment preflight before activation.",
      ],
      source_trace_required: true,
      approval_status: "blocked",
      content_hash: "local_workspace_policy",
      approval_invalidated_at: null,
      created_at: LOCAL_NOW,
      updated_at: LOCAL_NOW,
    },
  ];
}

export async function listMemoryPolicies(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<MemoryPoliciesResponse> {
  return cpJson<MemoryPoliciesResponse>(
    `/agents/${encodeURIComponent(agentId)}/memory-policies`,
    {
      ...opts,
      fallback: { items: localMemoryPolicies(agentId) },
    },
  );
}

export async function upsertMemoryPolicy(
  agentId: string,
  input: MemoryPolicyInput,
  opts: UxWireupClientOptions = {},
): Promise<MemoryPolicy> {
  return cpJson<MemoryPolicy>(
    `/agents/${encodeURIComponent(agentId)}/memory-policies/${encodeURIComponent(
      input.scope,
    )}`,
    {
      ...opts,
      method: "PUT",
      body: input,
      fallback: {
        ...localMemoryPolicies(agentId).find(
          (policy) => policy.scope === input.scope,
        )!,
        ...input,
        approval_status:
          input.scope === "user" || input.scope === "workspace"
            ? "review_required"
            : "draft",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function approveMemoryPolicy(
  agentId: string,
  scope: MemoryPolicyScope,
  opts: UxWireupClientOptions = {},
): Promise<MemoryPolicy> {
  const fallback =
    localMemoryPolicies(agentId).find((policy) => policy.scope === scope) ??
    localMemoryPolicies(agentId)[0]!;
  return cpJson<MemoryPolicy>(
    `/agents/${encodeURIComponent(agentId)}/memory-policies/${encodeURIComponent(
      scope,
    )}/approve`,
    {
      ...opts,
      method: "POST",
      fallback: {
        ...fallback,
        approval_status: "approved",
        approval_invalidated_at: null,
        updated_at: new Date().toISOString(),
      },
    },
  );
}

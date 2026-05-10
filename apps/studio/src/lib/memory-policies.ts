import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type MemoryPolicyScope =
  | "turn"
  | "conversation"
  | "session"
  | "user"
  | "account"
  | "organization"
  | "task"
  | "agent"
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

type MemoryPolicyClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

const LOCAL_NOW = new Date(0).toISOString();

function localPolicy(
  agentId: string,
  input: {
    id: string;
    scope: MemoryPolicyScope;
    allowed_memory_types: string[];
    retention: string;
    consent_requirement: string;
    pii_policy: string;
    delete_behavior: string;
    privacy_implications: string[];
    approval_status: MemoryPolicyApprovalStatus;
  },
): MemoryPolicy {
  return {
    workspace_id: "local",
    agent_id: agentId,
    source_trace_required: true,
    content_hash: `local_${input.scope}_policy`,
    approval_invalidated_at: null,
    created_at: LOCAL_NOW,
    updated_at: LOCAL_NOW,
    ...input,
  };
}

export function localMemoryPolicies(agentId: string): MemoryPolicy[] {
  return [
    localPolicy(agentId, {
      id: "mp_local_session",
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
      approval_status: "draft",
    }),
    localPolicy(agentId, {
      id: "mp_local_user",
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
      approval_status: "review_required",
    }),
    localPolicy(agentId, {
      id: "mp_local_account",
      scope: "account",
      allowed_memory_types: ["plan_tier", "account_entitlement"],
      retention: "Keep account facts for 90 days unless account data changes.",
      consent_requirement:
        "Admin-approved account memory only; users are notified through account terms.",
      pii_policy: "Account memory cannot include user-level secrets or payment data.",
      delete_behavior: "Delete or re-sync when account ownership or plan changes.",
      privacy_implications: [
        "Account memory can affect all users under the same customer account.",
        "Writes must cite the lookup trace and source system version.",
      ],
      approval_status: "review_required",
    }),
    localPolicy(agentId, {
      id: "mp_local_organization",
      scope: "organization",
      allowed_memory_types: ["routing_policy", "tenant_preference"],
      retention:
        "Retain organization policy memory until superseded by governance.",
      consent_requirement:
        "Workspace admin approval and governance notice required before activation.",
      pii_policy: "Organization memory cannot store individual PII.",
      delete_behavior:
        "Delete through governance request or replace with a superseding policy.",
      privacy_implications: [
        "Organization memory can affect every agent user in the tenant.",
        "Policy changes must appear in deployment preflight.",
      ],
      approval_status: "review_required",
    }),
    localPolicy(agentId, {
      id: "mp_local_task",
      scope: "task",
      allowed_memory_types: ["task_context", "retrieval_context"],
      retention: "Expires when the task or replay branch closes.",
      consent_requirement: "Covered by the active task and trace consent.",
      pii_policy: "Task memory may not be promoted to durable scope automatically.",
      delete_behavior: "Delete when the task is closed or replay context is cleared.",
      privacy_implications: [
        "Task memory only affects the active task, replay, or simulator branch.",
      ],
      approval_status: "draft",
    }),
    localPolicy(agentId, {
      id: "mp_local_agent",
      scope: "agent",
      allowed_memory_types: ["behavior_guardrail", "accepted_catch"],
      retention: "Version-bound retention; supersede with accepted behavior changes.",
      consent_requirement:
        "Builder approval required before agent-scope memory changes behavior.",
      pii_policy: "Agent memory cannot contain user PII or customer secrets.",
      delete_behavior: "Supersede or delete through a governed behavior change.",
      privacy_implications: [
        "Agent memory can affect every conversation handled by this agent.",
        "Changes must link to a catch, incident, eval, or accepted change package.",
      ],
      approval_status: "review_required",
    }),
    localPolicy(agentId, {
      id: "mp_local_workspace",
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
      approval_status: "blocked",
    }),
  ];
}

export async function listMemoryPolicies(
  agentId: string,
  opts: MemoryPolicyClientOptions = {},
): Promise<MemoryPoliciesResponse> {
  return cpJson<MemoryPoliciesResponse>(
    `/agents/${encodeURIComponent(agentId)}/memory-policies`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: { items: localMemoryPolicies(agentId) },
    },
  );
}

export async function upsertMemoryPolicy(
  agentId: string,
  input: MemoryPolicyInput,
  opts: MemoryPolicyClientOptions = {},
): Promise<MemoryPolicy> {
  return cpJson<MemoryPolicy>(
    `/agents/${encodeURIComponent(agentId)}/memory-policies/${encodeURIComponent(
      input.scope,
    )}`,
    {
      ...opts,
      method: "PUT",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localMemoryPolicies(agentId).find(
          (policy) => policy.scope === input.scope,
        )!,
        ...input,
        approval_status:
          input.scope === "user" ||
          input.scope === "account" ||
          input.scope === "organization" ||
          input.scope === "agent" ||
          input.scope === "workspace"
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
  opts: MemoryPolicyClientOptions = {},
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
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...fallback,
        approval_status: "approved",
        approval_invalidated_at: null,
        updated_at: new Date().toISOString(),
      },
    },
  );
}

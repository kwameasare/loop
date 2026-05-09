import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type ToolSideEffectLevel =
  | "unknown"
  | "read"
  | "write"
  | "money_movement"
  | "external_message";
export type ToolSandboxStatus = "mock" | "sandbox" | "disabled";
export type ToolLiveStatus =
  | "disabled"
  | "review_required"
  | "approved"
  | "blocked";

export interface ToolContract {
  id: string;
  workspace_id: string;
  agent_id: string;
  tool_id: string;
  name: string;
  description: string;
  side_effect_level: ToolSideEffectLevel;
  pii_access: boolean;
  money_movement: boolean;
  rate_limits: Record<string, unknown>;
  budget_limits: Record<string, unknown>;
  sandbox_status: ToolSandboxStatus;
  live_status: ToolLiveStatus;
  owner_user_id: string;
  approval_policy_id: string;
  failure_behavior: string;
  compensation_behavior: string;
  content_hash: string;
  approval_invalidated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ToolContractsResponse {
  items: ToolContract[];
}

export type ToolContractInput = Pick<
  ToolContract,
  | "name"
  | "description"
  | "side_effect_level"
  | "pii_access"
  | "money_movement"
  | "rate_limits"
  | "budget_limits"
  | "sandbox_status"
  | "owner_user_id"
  | "approval_policy_id"
  | "failure_behavior"
  | "compensation_behavior"
>;

function localContract(agentId: string, toolId: string): ToolContract {
  const now = new Date(0).toISOString();
  const isRefund = /refund|payment|charge/i.test(toolId);
  return {
    id: `tc_local_${toolId}`,
    workspace_id: "local",
    agent_id: agentId,
    tool_id: toolId,
    name: toolId,
    description: isRefund
      ? "Create a refund only after policy and approval checks."
      : "Read-only lookup tool contract.",
    side_effect_level: isRefund ? "money_movement" : "read",
    pii_access: false,
    money_movement: isRefund,
    rate_limits: { per_minute: isRefund ? 20 : 600 },
    budget_limits: isRefund ? { max_per_call_cents: 50_000 } : {},
    sandbox_status: "sandbox",
    live_status: isRefund ? "review_required" : "approved",
    owner_user_id: "workspace-builder",
    approval_policy_id: isRefund ? "policy-money-movement" : "policy-read-only",
    failure_behavior: isRefund
      ? "Escalate instead of promising a refund."
      : "Answer with uncertainty if lookup fails.",
    compensation_behavior: isRefund
      ? "Void pending refund when downstream write fails."
      : "No compensation required for read-only calls.",
    content_hash: `local_hash_${toolId}`,
    approval_invalidated_at: null,
    created_at: now,
    updated_at: now,
  };
}

export function localToolContracts(
  agentId: string,
  toolIds: string[],
): ToolContract[] {
  return toolIds.map((toolId) => localContract(agentId, toolId));
}

export async function listToolContracts(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<ToolContractsResponse> {
  return cpJson<ToolContractsResponse>(
    `/agents/${encodeURIComponent(agentId)}/tool-contracts`,
    {
      ...opts,
      fallback: { items: [] },
    },
  );
}

export async function upsertToolContract(
  agentId: string,
  toolId: string,
  input: ToolContractInput,
  opts: UxWireupClientOptions = {},
): Promise<ToolContract> {
  return cpJson<ToolContract>(
    `/agents/${encodeURIComponent(agentId)}/tool-contracts/${encodeURIComponent(
      toolId,
    )}`,
    {
      ...opts,
      method: "PUT",
      body: input,
      fallback: {
        ...localContract(agentId, toolId),
        ...input,
        tool_id: toolId,
        updated_at: new Date(0).toISOString(),
      },
    },
  );
}

export async function promoteToolContract(
  agentId: string,
  toolId: string,
  opts: UxWireupClientOptions = {},
): Promise<ToolContract> {
  const fallback = localContract(agentId, toolId);
  return cpJson<ToolContract>(
    `/agents/${encodeURIComponent(agentId)}/tool-contracts/${encodeURIComponent(
      toolId,
    )}/promote`,
    {
      ...opts,
      method: "POST",
      fallback: {
        ...fallback,
        live_status: "approved",
        approval_invalidated_at: null,
      },
    },
  );
}

import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type PreApprovedRiskCeiling = "low" | "medium" | "high";
export type PreApprovedClassStatus =
  | "active"
  | "revoked"
  | "expired"
  | "invalidated";

export interface PreApprovedClass {
  id: string;
  workspace_id: string;
  agent_id: string;
  granted_by_user_id: string;
  granted_to_user_id: string;
  team_id: string;
  allowed_change_types: string[];
  excluded_change_types: string[];
  risk_ceiling: PreApprovedRiskCeiling;
  expires_at: string;
  status: PreApprovedClassStatus;
  reason: string;
  created_at: string;
  updated_at: string;
  revoked_at: string | null;
  expired_at?: string | null;
  invalidated_at: string | null;
  used_by_change_packages: string[];
}

export interface PreApprovedClassListResponse {
  items: PreApprovedClass[];
}

export interface PreApprovedClassCreateInput {
  granted_to_user_id?: string;
  team_id?: string;
  allowed_change_types: string[];
  excluded_change_types?: string[];
  risk_ceiling: PreApprovedRiskCeiling;
  expires_at: string;
  reason?: string;
}

export async function listPreApprovedClasses(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<PreApprovedClassListResponse> {
  return cpJson<PreApprovedClassListResponse>(
    `/agents/${encodeURIComponent(agentId)}/pre-approved-classes`,
    {
      ...opts,
      allowFallback: false,
      fallback: { items: [] },
    },
  );
}

export async function createPreApprovedClass(
  agentId: string,
  input: PreApprovedClassCreateInput,
  opts: UxWireupClientOptions = {},
): Promise<PreApprovedClass> {
  return cpJson<PreApprovedClass>(
    `/agents/${encodeURIComponent(agentId)}/pre-approved-classes`,
    {
      ...opts,
      method: "POST",
      body: {
        granted_to_user_id: input.granted_to_user_id ?? "",
        team_id: input.team_id ?? "",
        allowed_change_types: input.allowed_change_types,
        excluded_change_types: input.excluded_change_types ?? [],
        risk_ceiling: input.risk_ceiling,
        expires_at: input.expires_at,
        reason: input.reason ?? "",
      },
      allowFallback: false,
      fallback: {} as PreApprovedClass,
    },
  );
}

export async function revokePreApprovedClass(
  agentId: string,
  classId: string,
  opts: UxWireupClientOptions = {},
): Promise<PreApprovedClass> {
  return cpJson<PreApprovedClass>(
    `/agents/${encodeURIComponent(
      agentId,
    )}/pre-approved-classes/${encodeURIComponent(classId)}/revoke`,
    {
      ...opts,
      method: "POST",
      allowFallback: false,
      fallback: {} as PreApprovedClass,
    },
  );
}

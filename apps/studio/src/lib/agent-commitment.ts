import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type CommitmentStatus = "draft" | "accepted" | "superseded" | "archived";

export interface CommitmentBody {
  business_responsibility: string;
  target_users: string;
  owner_user_id: string;
  backup_owner_user_id: string;
  worst_case_failure: string;
  channels: string[];
  systems_touched: string[];
  regions: string[];
  languages: string[];
  success_metric: string;
  compliance_domain: string;
  expected_volume: string;
  launch_date: string;
  budget_target: string;
  out_of_scope: string;
  escalation_policy: string;
}

export interface CommitmentSummary {
  responsibility: string;
  audience: string;
  owner: string;
  backup_owner: string;
  risk: string;
  channels: string[];
  systems_touched: string[];
  regions: string[];
  languages: string[];
  readiness: "complete" | "incomplete";
  missing_required_fields: string[];
}

export interface CommitmentDocument {
  id: string;
  agent_id: string;
  workspace_id: string;
  version: number;
  body: CommitmentBody;
  structured_summary: CommitmentSummary;
  owner_user_id: string;
  status: CommitmentStatus;
  content_hash: string;
  created_from: string;
  created_at: string;
  updated_at: string;
  accepted_at: string | null;
  superseded_at: string | null;
}

export interface CommitmentDraftInput {
  body: CommitmentBody;
  created_from?: string;
}

export interface CommitmentHistoryResponse {
  items: CommitmentDocument[];
}

type CommitmentClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

export const EMPTY_COMMITMENT_BODY: CommitmentBody = {
  business_responsibility: "",
  target_users: "",
  owner_user_id: "",
  backup_owner_user_id: "",
  worst_case_failure: "",
  channels: [],
  systems_touched: [],
  regions: [],
  languages: [],
  success_metric: "",
  compliance_domain: "",
  expected_volume: "",
  launch_date: "",
  budget_target: "",
  out_of_scope: "",
  escalation_policy: "",
};

export const REQUIRED_COMMITMENT_FIELDS = [
  "business_responsibility",
  "target_users",
  "owner_user_id",
  "worst_case_failure",
  "channels",
  "systems_touched",
  "regions",
  "languages",
] as const;

export type RequiredCommitmentField =
  (typeof REQUIRED_COMMITMENT_FIELDS)[number];

const FIELD_LABELS: Record<RequiredCommitmentField, string> = {
  business_responsibility: "Business responsibility",
  target_users: "Target users",
  owner_user_id: "Owner",
  worst_case_failure: "Worst-case failure",
  channels: "Channels",
  systems_touched: "Systems touched",
  regions: "Regions",
  languages: "Languages",
};

export function commitmentFieldLabel(field: string): string {
  return FIELD_LABELS[field as RequiredCommitmentField] ?? field;
}

export function parseList(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function missingCommitmentFields(
  body: CommitmentBody,
): RequiredCommitmentField[] {
  return REQUIRED_COMMITMENT_FIELDS.filter((field) => {
    const value = body[field];
    return Array.isArray(value)
      ? value.filter(Boolean).length === 0
      : value.trim().length === 0;
  });
}

export function buildLocalCommitmentDocument(
  agentId: string,
  body: CommitmentBody = EMPTY_COMMITMENT_BODY,
): CommitmentDocument {
  const missing = missingCommitmentFields(body);
  return {
    id: "commitment_unconfigured",
    agent_id: agentId,
    workspace_id: "",
    version: 0,
    body,
    structured_summary: {
      responsibility: body.business_responsibility,
      audience: body.target_users,
      owner: body.owner_user_id,
      backup_owner: body.backup_owner_user_id,
      risk: body.worst_case_failure,
      channels: body.channels,
      systems_touched: body.systems_touched,
      regions: body.regions,
      languages: body.languages,
      readiness: missing.length === 0 ? "complete" : "incomplete",
      missing_required_fields: missing,
    },
    owner_user_id: body.owner_user_id,
    status: "draft",
    content_hash: "unconfigured",
    created_from: "studio:local_unconfigured",
    created_at: "",
    updated_at: "",
    accepted_at: null,
    superseded_at: null,
  };
}

export async function fetchCurrentCommitment(
  agentId: string,
  opts: CommitmentClientOptions = {},
): Promise<CommitmentDocument> {
  return cpJson<CommitmentDocument>(
    `/agents/${encodeURIComponent(agentId)}/commitment/current`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: buildLocalCommitmentDocument(agentId),
    },
  );
}

export async function listCommitments(
  agentId: string,
  opts: CommitmentClientOptions = {},
): Promise<CommitmentHistoryResponse> {
  const fallbackDocument = buildLocalCommitmentDocument(agentId);
  return cpJson<CommitmentHistoryResponse>(
    `/agents/${encodeURIComponent(agentId)}/commitments`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: { items: [fallbackDocument] },
    },
  );
}

export async function saveCommitmentDraft(
  agentId: string,
  input: CommitmentDraftInput,
  opts: CommitmentClientOptions = {},
): Promise<CommitmentDocument> {
  const fallback = buildLocalCommitmentDocument(agentId, input.body);
  return cpJson<CommitmentDocument>(
    `/agents/${encodeURIComponent(agentId)}/commitment`,
    {
      ...opts,
      method: "POST",
      body: {
        body: input.body,
        created_from: input.created_from ?? "studio:agent_contract",
      },
      allowFallback: opts.allowFixture === true,
      fallback,
    },
  );
}

export async function acceptCommitment(
  agentId: string,
  opts: CommitmentClientOptions = {},
): Promise<CommitmentDocument> {
  return cpJson<CommitmentDocument>(
    `/agents/${encodeURIComponent(agentId)}/commitment/accept`,
    {
      ...opts,
      method: "POST",
      allowFallback: opts.allowFixture === true,
      fallback: buildLocalCommitmentDocument(agentId),
    },
  );
}

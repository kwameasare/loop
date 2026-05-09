import {
  buildLocalCommitmentDocument,
  type CommitmentDocument,
} from "@/lib/agent-commitment";
import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type HandoffRiskSeverity = "blocking" | "advisory" | "info";

export interface HandoffRisk {
  id: string;
  severity: HandoffRiskSeverity;
  title: string;
  detail: string;
  evidence_ref: string;
}

export interface WalkthroughSection {
  id: string;
  title: string;
  summary: string;
  count: number;
  evidence_refs: string[];
}

export interface OwnershipTransfer {
  id: string;
  workspace_id: string;
  agent_id: string;
  previous_owner_user_id: string;
  new_owner_user_id: string;
  backup_owner_user_id: string;
  reason: string;
  acknowledged_risk_ids: string[];
  history_walkthrough_id: string;
  created_by_user_id: string;
  created_at: string;
}

export interface AgentHandoffModel {
  agent: {
    id: string;
    name: string;
    slug: string;
    description: string;
  };
  owner_user_id: string;
  backup_owner_user_id: string;
  commitment: CommitmentDocument;
  open_risks: HandoffRisk[];
  walkthrough_sections: WalkthroughSection[];
  transfers: OwnershipTransfer[];
  generated_at: string;
}

export interface OwnershipTransferInput {
  new_owner_user_id: string;
  backup_owner_user_id?: string;
  reason?: string;
  acknowledged_risk_ids?: string[];
}

const LOCAL_NOW = new Date(0).toISOString();

export function localAgentHandoff(agentId: string): AgentHandoffModel {
  const commitment = buildLocalCommitmentDocument(agentId);
  return {
    agent: {
      id: agentId,
      name: "Local agent",
      slug: "local-agent",
      description: "Local fallback handoff model.",
    },
    owner_user_id: commitment.body.owner_user_id,
    backup_owner_user_id: commitment.body.backup_owner_user_id,
    commitment,
    open_risks: [
      {
        id: "commitment_missing_fields",
        severity: "blocking",
        title: "Commitment is incomplete",
        detail: "Complete the Agent Contract before handoff.",
        evidence_ref: `commitment/${commitment.id}`,
      },
    ],
    walkthrough_sections: [
      {
        id: "commitments",
        title: "Commitment changes",
        summary: "Local Commitment Document fallback.",
        count: 1,
        evidence_refs: [`commitment/${commitment.id}`],
      },
      {
        id: "change-packages",
        title: "Change Packages and approvals",
        summary: "No live Change Packages loaded.",
        count: 0,
        evidence_refs: [],
      },
      {
        id: "incidents",
        title: "Incidents and candidate evals",
        summary: "No live incidents loaded.",
        count: 0,
        evidence_refs: [],
      },
      {
        id: "important-comments",
        title: "Important reviewer comments",
        summary: "No resolved reviewer comments loaded.",
        count: 0,
        evidence_refs: [],
      },
    ],
    transfers: [],
    generated_at: LOCAL_NOW,
  };
}

export async function fetchAgentHandoff(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<AgentHandoffModel> {
  return cpJson<AgentHandoffModel>(
    `/agents/${encodeURIComponent(agentId)}/handoff`,
    {
      ...opts,
      fallback: localAgentHandoff(agentId),
    },
  );
}

export async function transferAgentOwner(
  agentId: string,
  input: OwnershipTransferInput,
  opts: UxWireupClientOptions & { fallbackModel?: AgentHandoffModel } = {},
): Promise<AgentHandoffModel> {
  const fallback = opts.fallbackModel ?? localAgentHandoff(agentId);
  const nextCommitment = {
    ...fallback.commitment,
    body: {
      ...fallback.commitment.body,
      owner_user_id: input.new_owner_user_id,
      backup_owner_user_id: input.backup_owner_user_id ?? "",
    },
    owner_user_id: input.new_owner_user_id,
    created_from: "handoff:ownership_transfer",
    updated_at: new Date().toISOString(),
  };
  return cpJson<AgentHandoffModel>(
    `/agents/${encodeURIComponent(agentId)}/handoff/transfer`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        ...fallback,
        owner_user_id: input.new_owner_user_id,
        backup_owner_user_id: input.backup_owner_user_id ?? "",
        commitment: nextCommitment,
        transfers: [
          {
            id: `handoff_local_${Date.now()}`,
            workspace_id: fallback.commitment.workspace_id,
            agent_id: agentId,
            previous_owner_user_id: fallback.owner_user_id,
            new_owner_user_id: input.new_owner_user_id,
            backup_owner_user_id: input.backup_owner_user_id ?? "",
            reason: input.reason ?? "",
            acknowledged_risk_ids: input.acknowledged_risk_ids ?? [],
            history_walkthrough_id: `walk_local_${Date.now()}`,
            created_by_user_id: "local-builder",
            created_at: new Date().toISOString(),
          },
          ...fallback.transfers,
        ],
        generated_at: new Date().toISOString(),
      },
    },
  );
}

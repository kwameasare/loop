import type {
  CommitmentBody,
  CommitmentDocument,
} from "@/lib/agent-commitment";
import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";
import type { AgentSummary } from "@/lib/cp-api";

export type AgentIntakePath =
  | "business_intent"
  | "legacy_import"
  | "enterprise_template";

export type AgentIntakeState =
  | "empty"
  | "uploading"
  | "parsing"
  | "analyzing"
  | "needs_clarification"
  | "draft_ready"
  | "failed"
  | "cancelled";

export type AgentIntakeArtifactKind =
  | "pdf"
  | "faq"
  | "runbook"
  | "transcript"
  | "botpress_export"
  | "dialogflow_export"
  | "rasa_export"
  | "zendesk_export"
  | "intercom_export"
  | "openapi"
  | "postman"
  | "curl"
  | "devtools_fetch"
  | "other";

export interface AgentIntakeArtifactInput {
  name: string;
  kind: AgentIntakeArtifactKind;
  text: string;
  source_ref: string;
}

export interface AgentIntakeCreateInput {
  agent_name: string;
  slug: string;
  creation_path: AgentIntakePath;
  contract: CommitmentBody;
  artifacts: AgentIntakeArtifactInput[];
  capabilities: string[];
  template_id?: string;
}

export interface AgentIntakeRecord {
  id: string;
  workspace_id: string;
  agent_id: string;
  state: AgentIntakeState;
  creation_path: AgentIntakePath;
  jobs: Array<{ name: string; state: string; count: number }>;
  artifact_reports: Array<Record<string, unknown>>;
  intent_map: Array<Record<string, unknown>>;
  contradictions: Array<Record<string, unknown>>;
  sensitive_data_findings: Array<Record<string, unknown>>;
  candidate_tools: Array<Record<string, unknown>>;
  candidate_channels: Array<Record<string, unknown>>;
  candidate_memory_policy: Record<string, unknown>;
  candidate_eval_cases: Array<Record<string, unknown>>;
  risk_notes: Array<Record<string, unknown>>;
  missing_information: Array<Record<string, unknown>>;
  readiness: {
    score: number;
    ready: string[];
    needs_attention: string[];
    landing: string;
  };
  created_object_refs: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
  agent?: AgentSummary;
  commitment?: CommitmentDocument;
}

export interface AgentIntakeCreateResult extends AgentIntakeRecord {
  agent: AgentSummary;
  commitment: CommitmentDocument;
}

export interface AgentIntakeOptions extends UxWireupClientOptions {
  workspaceId?: string;
}

function localAgent(
  input: AgentIntakeCreateInput,
  workspaceId: string,
): AgentSummary {
  return {
    id: `local_${input.slug || "agent"}`,
    workspace_id: workspaceId,
    name: input.agent_name,
    slug: input.slug,
    description: input.contract.business_responsibility,
    active_version: null,
    updated_at: new Date(0).toISOString(),
  };
}

function localIntakeResult(
  input: AgentIntakeCreateInput,
  workspaceId = "local-workspace",
): AgentIntakeCreateResult {
  const agent = localAgent(input, workspaceId);
  const channels = input.contract.channels.filter(Boolean);
  const tools = input.contract.systems_touched.filter(Boolean);
  return {
    id: `intake_${input.slug || "local"}`,
    workspace_id: workspaceId,
    agent_id: agent.id,
    state: "draft_ready",
    creation_path: input.creation_path,
    jobs: [
      {
        name: "parse_artifacts",
        state: "completed",
        count: input.artifacts.length,
      },
      {
        name: "extract_intents",
        state: "completed",
        count: input.capabilities.length + 1,
      },
      { name: "infer_tools", state: "completed", count: tools.length },
      { name: "infer_channels", state: "completed", count: channels.length },
      { name: "draft_agent_plan", state: "completed", count: 1 },
    ],
    artifact_reports: input.artifacts.map((artifact) => ({
      name: artifact.name,
      kind: artifact.kind,
      status: artifact.text || artifact.source_ref ? "parsed" : "needs_content",
    })),
    intent_map: input.capabilities.map((capability, index) => ({
      id: `intent_${index + 1}`,
      label: capability,
      confidence: "medium",
    })),
    contradictions: [],
    sensitive_data_findings: [],
    candidate_tools: tools.map((system) => ({
      tool_id: `mock_${system.toLowerCase().replace(/\W+/g, "_")}`,
      name: `${system} mock tool`,
    })),
    candidate_channels: channels.map((channel) => ({
      channel,
      status: "draft",
    })),
    candidate_memory_policy: {
      scope: "conversation",
      status: "draft",
    },
    candidate_eval_cases: [
      { name: "Happy path follows the commitment", source: "intake:contract" },
      {
        name: "Worst-case failure is refused or escalated",
        source: "intake:risk",
      },
      { name: "Channel format is preserved", source: "intake:channel" },
    ],
    risk_notes: [
      { severity: "medium", message: input.contract.worst_case_failure },
    ],
    missing_information: [],
    readiness: {
      score: 72,
      ready: [
        "Mission defined",
        "Commitment Document drafted",
        `${channels.length} sandbox channel binding(s) created`,
        `${tools.length} mock tool contract(s) created`,
      ],
      needs_attention: ["Run first simulation suite before preflight."],
      landing: `/agents/${agent.id}`,
    },
    created_object_refs: {
      agent_id: agent.id,
      channel_bindings: channels,
      tool_contracts: tools,
    },
    created_by: "local",
    created_at: new Date(0).toISOString(),
    updated_at: new Date(0).toISOString(),
    agent,
    commitment: {
      id: "commitment_local",
      agent_id: agent.id,
      workspace_id: workspaceId,
      version: 1,
      body: input.contract,
      structured_summary: {
        responsibility: input.contract.business_responsibility,
        audience: input.contract.target_users,
        owner: input.contract.owner_user_id,
        backup_owner: input.contract.backup_owner_user_id,
        risk: input.contract.worst_case_failure,
        channels: input.contract.channels,
        systems_touched: input.contract.systems_touched,
        regions: input.contract.regions,
        languages: input.contract.languages,
        readiness: "complete",
        missing_required_fields: [],
      },
      owner_user_id: input.contract.owner_user_id,
      status: "draft",
      content_hash: "local",
      created_from: "agent_intake:local",
      created_at: new Date(0).toISOString(),
      updated_at: new Date(0).toISOString(),
      accepted_at: null,
      superseded_at: null,
    },
  };
}

export async function createAgentIntake(
  workspaceId: string,
  input: AgentIntakeCreateInput,
  opts: UxWireupClientOptions = {},
): Promise<AgentIntakeCreateResult> {
  return cpJson<AgentIntakeCreateResult>(
    `/workspaces/${encodeURIComponent(workspaceId)}/agent-intakes`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: localIntakeResult(input, workspaceId),
    },
  );
}

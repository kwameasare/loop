import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type MigrationRunStatus =
  | "imported"
  | "mapped"
  | "parity_ready"
  | "cutover_active"
  | "cutover_complete"
  | "rolled_back";

export type MigrationInventorySeverity = "ok" | "advisory" | "blocking";
export type CutoverStageStatus =
  | "pending"
  | "in_progress"
  | "passed"
  | "halted";
export type MigrationSource =
  | "botpress"
  | "dialogflow_cx"
  | "rasa"
  | "zendesk"
  | "intercom"
  | "custom_files"
  | "conversation_transcripts";

export interface MigrationSourceDefinition {
  id: MigrationSource;
  label: string;
  archiveLabel: string;
  defaultArchive: string;
  description: string;
  acceptedInputs: string[];
  defaultInventory: Record<string, number>;
}

export const MIGRATION_SOURCES: readonly MigrationSourceDefinition[] = [
  {
    id: "botpress",
    label: "Botpress .bpz",
    archiveLabel: "Botpress archive",
    defaultArchive: "acme-refunds.bpz",
    description:
      "Flows, nodes, KBs, actions, integrations, channels, and transcripts.",
    acceptedInputs: ["Botpress .bpz export"],
    defaultInventory: { integrations: 0, unsupported_nodes: 0 },
  },
  {
    id: "dialogflow_cx",
    label: "Dialogflow CX",
    archiveLabel: "CX export",
    defaultArchive: "dialogflow-cx-agent.zip",
    description:
      "Flows, pages, intents, entities, fulfillment, webhooks, and transcripts.",
    acceptedInputs: ["CX agent export zip", "Flows/pages JSON"],
    defaultInventory: { webhooks: 0, fulfillment: 0 },
  },
  {
    id: "rasa",
    label: "Rasa project",
    archiveLabel: "Rasa project",
    defaultArchive: "rasa-project.zip",
    description:
      "Domain, NLU, stories, rules, forms, actions, and transcripts.",
    acceptedInputs: ["domain.yml", "nlu.yml", "stories.yml", "rules.yml"],
    defaultInventory: { actions: 0 },
  },
  {
    id: "zendesk",
    label: "Zendesk",
    archiveLabel: "Zendesk export",
    defaultArchive: "zendesk-support-export.zip",
    description:
      "Macros, triggers, help center articles, integrations, channels, and conversations.",
    acceptedInputs: [
      "Automations/macros JSON",
      "Help Center export",
      "Conversation CSV",
    ],
    defaultInventory: { integrations: 0 },
  },
  {
    id: "intercom",
    label: "Intercom",
    archiveLabel: "Intercom export",
    defaultArchive: "intercom-content-conversations.zip",
    description:
      "Articles, workflows, handoff rules, integrations, channels, and conversations.",
    acceptedInputs: [
      "Article export",
      "Conversation export",
      "Fin handoff transcript",
    ],
    defaultInventory: { integrations: 0 },
  },
  {
    id: "custom_files",
    label: "Custom files",
    archiveLabel: "Custom bundle",
    defaultArchive: "agent-files.zip",
    description:
      "JSON, YAML, CSV, OpenAPI, tables, policy files, and transcripts.",
    acceptedInputs: ["JSON", "YAML", "CSV", "OpenAPI", "Transcript files"],
    defaultInventory: { integrations: 0 },
  },
  {
    id: "conversation_transcripts",
    label: "Transcripts only",
    archiveLabel: "Transcript file",
    defaultArchive: "support-transcripts.csv",
    description:
      "Infer capabilities, risks, and evals from conversation transcripts.",
    acceptedInputs: ["CSV", "JSONL", "Chat transcripts"],
    defaultInventory: {},
  },
] as const;

export function migrationSourceById(
  source: MigrationSource,
): MigrationSourceDefinition {
  return (
    MIGRATION_SOURCES.find((item) => item.id === source) ??
    MIGRATION_SOURCES[0]!
  );
}

export interface MigrationInventoryItem {
  id: string;
  kind: string;
  label: string;
  count: number;
  loop_target: string;
  confidence: number;
  severity: MigrationInventorySeverity;
  evidence_ref: string;
}

export interface MigrationLineageStep {
  id: string;
  label: string;
  status: string;
  evidence_ref: string;
  detail: string;
}

export interface MigrationReadinessRecord {
  overall_score: number;
  parity_passing: number;
  parity_total: number;
  blocking_count: number;
  advisory_count: number;
}

export interface MigrationCutoverStage {
  id: string;
  percent: number;
  duration_minutes: number;
  status: CutoverStageStatus;
  guardrails: string[];
}

export interface MigrationCutoverEvent {
  id: string;
  action: string;
  stage_id: string;
  actor_sub: string;
  evidence_ref: string;
  created_at: string;
}

export interface MigrationRun {
  id: string;
  workspace_id: string;
  source: MigrationSource;
  source_profile: {
    label: string;
    accepted_inputs: string[];
    primary_artifacts: string[];
    verification: string;
  };
  archive_name: string;
  archive_sha: string;
  target_agent_id: string;
  target_agent_name: string;
  target_branch_id: string;
  target_change_set_id: string;
  commitment_document_id: string;
  status: MigrationRunStatus;
  inventory: MigrationInventoryItem[];
  lineage_steps: MigrationLineageStep[];
  readiness: MigrationReadinessRecord;
  cutover_stages: MigrationCutoverStage[];
  cutover_events: MigrationCutoverEvent[];
  rollback_triggers: Array<Record<string, unknown>>;
  created_by_user_id: string;
  created_at: string;
  updated_at: string;
  inventory_total?: number;
}

export interface MigrationImportInput {
  source?: MigrationSource;
  archive_name: string;
  archive_sha?: string;
  target_agent_name: string;
  target_agent_slug?: string;
  business_responsibility?: string;
  channels?: string[];
  inventory?: Record<string, number>;
  transcript_count?: number;
}

export interface MigrationRunsResponse {
  items: MigrationRun[];
}

type MigrationRunClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

type MigrationCutoverClientOptions = MigrationRunClientOptions & {
  fallbackRun?: MigrationRun;
};

const LOCAL_NOW = new Date(0).toISOString();

export function localMigrationRun(workspaceId: string): MigrationRun {
  const source = migrationSourceById("botpress");
  return {
    id: "mig_local_botpress",
    workspace_id: workspaceId,
    source: source.id,
    source_profile: {
      label: source.label,
      accepted_inputs: [...source.acceptedInputs],
      primary_artifacts: [
        "intents",
        "workflows",
        "nodes",
        "knowledge_sources",
        "integrations",
        "channels",
        "transcripts",
      ],
      verification: "public_export_format",
    },
    archive_name: "acme-refunds.bpz",
    archive_sha:
      "sha256:local00000000000000000000000000000000000000000000000000000000000",
    target_agent_id: "agent_local_migration",
    target_agent_name: "Acme Imported Concierge",
    target_branch_id: "br_local_migration",
    target_change_set_id: "cs_local_migration",
    commitment_document_id: "commit_local_migration",
    status: "parity_ready",
    inventory: [
      {
        id: "inv_intents",
        kind: "intents",
        label: "Intents",
        count: 42,
        loop_target: "capabilities",
        confidence: 92,
        severity: "ok",
        evidence_ref: "audit/migration/local/inventory/intents",
      },
    ],
    lineage_steps: [
      {
        id: "parse",
        label: "Parse source archive",
        status: "ok",
        evidence_ref: "audit/migration/local/parse",
        detail: "Parsed archive and preserved source artifact IDs.",
      },
    ],
    readiness: {
      overall_score: 95,
      parity_passing: 20,
      parity_total: 20,
      blocking_count: 0,
      advisory_count: 1,
    },
    cutover_stages: [
      {
        id: "canary_1pct",
        percent: 1,
        duration_minutes: 30,
        status: "in_progress",
        guardrails: ["shadow_agreement>=95%", "regression=0"],
      },
      {
        id: "canary_10pct",
        percent: 10,
        duration_minutes: 60,
        status: "pending",
        guardrails: ["regression<2", "cost_per_turn<150%"],
      },
      {
        id: "canary_100pct",
        percent: 100,
        duration_minutes: 0,
        status: "pending",
        guardrails: ["all-stages-passed"],
      },
    ],
    cutover_events: [],
    rollback_triggers: [],
    created_by_user_id: "local-builder",
    created_at: LOCAL_NOW,
    updated_at: LOCAL_NOW,
    inventory_total: 42,
  };
}

export async function listMigrationImports(
  workspaceId: string,
  opts: MigrationRunClientOptions = {},
): Promise<MigrationRunsResponse> {
  return cpJson<MigrationRunsResponse>(
    `/workspaces/${encodeURIComponent(workspaceId)}/migrations/imports`,
    {
      ...opts,
      allowFallback: opts.allowFixture === true,
      fallback: { items: [] },
    },
  );
}

export async function createMigrationImport(
  workspaceId: string,
  input: MigrationImportInput,
  opts: MigrationRunClientOptions = {},
): Promise<MigrationRun> {
  const source = input.source ?? "botpress";
  const sourceDefinition = migrationSourceById(source);
  const localRun = localMigrationRun(workspaceId);
  return cpJson<MigrationRun>(
    `/workspaces/${encodeURIComponent(workspaceId)}/migrations/imports`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localRun,
        source,
        source_profile: {
          ...localRun.source_profile,
          label: sourceDefinition.label,
          accepted_inputs: [...sourceDefinition.acceptedInputs],
        },
        archive_name: input.archive_name,
        target_agent_name: input.target_agent_name,
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function advanceMigrationCutover(
  workspaceId: string,
  migrationId: string,
  input: { stage_id: string; evidence_ref?: string },
  opts: MigrationCutoverClientOptions = {},
): Promise<MigrationRun> {
  const fallback = opts.fallbackRun ?? localMigrationRun(workspaceId);
  const stageIndex = fallback.cutover_stages.findIndex(
    (stage) => stage.id === input.stage_id,
  );
  const nextStages = fallback.cutover_stages.map((stage, index) => {
    if (stageIndex < 0) return stage;
    if (index === stageIndex) return { ...stage, status: "passed" as const };
    if (index === stageIndex + 1) {
      return { ...stage, status: "in_progress" as const };
    }
    return stage;
  });
  return cpJson<MigrationRun>(
    `/workspaces/${encodeURIComponent(
      workspaceId,
    )}/migrations/imports/${encodeURIComponent(migrationId)}/cutover/advance`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...fallback,
        status:
          stageIndex >= 0 && stageIndex === fallback.cutover_stages.length - 1
            ? "cutover_complete"
            : "cutover_active",
        cutover_stages: nextStages as MigrationCutoverStage[],
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function rollbackMigrationCutover(
  workspaceId: string,
  migrationId: string,
  input: { trigger_id?: string; reason?: string },
  opts: MigrationCutoverClientOptions = {},
): Promise<MigrationRun> {
  const fallback = opts.fallbackRun ?? localMigrationRun(workspaceId);
  return cpJson<MigrationRun>(
    `/workspaces/${encodeURIComponent(
      workspaceId,
    )}/migrations/imports/${encodeURIComponent(migrationId)}/cutover/rollback`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...fallback,
        status: "rolled_back",
        cutover_stages: fallback.cutover_stages.map((stage) =>
          stage.status === "passed" ? stage : { ...stage, status: "halted" },
        ) as MigrationCutoverStage[],
        updated_at: new Date().toISOString(),
      },
    },
  );
}

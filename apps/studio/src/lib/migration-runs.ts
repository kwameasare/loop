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
  source: string;
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
  source?: string;
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

const LOCAL_NOW = new Date(0).toISOString();

export function localMigrationRun(workspaceId: string): MigrationRun {
  return {
    id: "mig_local_botpress",
    workspace_id: workspaceId,
    source: "botpress",
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
  opts: UxWireupClientOptions = {},
): Promise<MigrationRunsResponse> {
  return cpJson<MigrationRunsResponse>(
    `/workspaces/${encodeURIComponent(workspaceId)}/migrations/imports`,
    {
      ...opts,
      fallback: { items: [] },
    },
  );
}

export async function createMigrationImport(
  workspaceId: string,
  input: MigrationImportInput,
  opts: UxWireupClientOptions = {},
): Promise<MigrationRun> {
  return cpJson<MigrationRun>(
    `/workspaces/${encodeURIComponent(workspaceId)}/migrations/imports`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        ...localMigrationRun(workspaceId),
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
  opts: UxWireupClientOptions & { fallbackRun?: MigrationRun } = {},
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
  opts: UxWireupClientOptions & { fallbackRun?: MigrationRun } = {},
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

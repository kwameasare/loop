/**
 * S270: Deploys helpers for the agent-detail "Deploys" tab.
 *
 * cp-api endpoints:
 *   GET  /v1/agents/{id}/deployments                  → { items: Deployment[] }
 *   POST /v1/agents/{id}/deployments/{dep_id}/promote → Deployment
 *   POST /v1/agents/{id}/deployments/{dep_id}/ramp    → Deployment
 *   POST /v1/agents/{id}/deployments/{dep_id}/pause   → Deployment
 *   POST /v1/agents/{id}/deployments/{dep_id}/rollback → Deployment
 *
 * Fixture data is available only through explicit test/demo opt-in.
 */

export type DeploymentStatus =
  | "pending"
  | "shadow"
  | "canary"
  | "ramp"
  | "live"
  | "paused"
  | "rolled_back"
  | "superseded";
export type DeploymentStage =
  | "shadow"
  | "canary"
  | "ramp"
  | "production"
  | "rolled_back"
  | "paused"
  | "failed";

export interface Deployment {
  id: string;
  agentId: string;
  versionId: string;
  changePackageId?: string;
  evidencePackId?: string;
  stage?: DeploymentStage;
  status: DeploymentStatus;
  /** Percentage of traffic routed to this deployment (0–100). */
  trafficPercent: number;
  channelScope?: string[];
  regionScope?: string[];
  segmentScope?: string[];
  holdTimeMinutes?: number;
  autoRollbackThresholds?: Record<string, unknown>;
  createdAt: string;
  promotedAt: string | null;
  pausedAt: string | null;
  rolledBackAt: string | null;
  notes: string | null;
}

export interface DeploymentStartInput {
  change_package_id: string;
  version_id?: string;
  stage?: "shadow" | "canary";
  traffic_percent?: number;
  channel_scope?: string[];
  region_scope?: string[];
  segment_scope?: string[];
  hold_time_minutes?: number;
  auto_rollback_thresholds?: Record<string, unknown>;
  notes?: string | null;
}

export interface EvidencePack {
  id: string;
  workspace_id: string;
  agent_id: string;
  version_id: string;
  deployment_id: string;
  change_package_id: string;
  version_manifest: Record<string, unknown>;
  behavior_diff_ref: string;
  tool_permission_diff_ref: string;
  knowledge_diff_ref: string;
  memory_policy_ref: string;
  channel_deployment_plan_ref: string;
  eval_results_ref: string;
  approval_records_ref: string;
  canary_results_ref: string;
  rollback_plan_ref: string;
  audit_log_ref: string;
  created_at: string;
  export_formats: string[];
}

export interface DeployHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
  allowFixture?: boolean;
}

export interface DeploymentListResponse {
  items: Deployment[];
  degraded_reason?: string | undefined;
}

function resolveBase(opts: DeployHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? (process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL)
      : undefined);
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function authHeaders(opts: DeployHelperOptions): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  return headers;
}

const FIXTURES: Record<string, Deployment[]> = {};

function seedFixtures(agentId: string): Deployment[] {
  if (!FIXTURES[agentId]) {
    FIXTURES[agentId] = [
      {
        id: "dep_002",
        agentId,
        versionId: "ver_v3",
        stage: "canary",
        status: "canary",
        trafficPercent: 25,
        createdAt: "2025-02-21T12:00:00Z",
        promotedAt: null,
        pausedAt: null,
        rolledBackAt: null,
        notes: "tools refactor",
      },
      {
        id: "dep_001",
        agentId,
        versionId: "ver_v2",
        stage: "production",
        status: "live",
        trafficPercent: 75,
        createdAt: "2025-02-19T09:14:00Z",
        promotedAt: "2025-02-19T09:30:00Z",
        pausedAt: null,
        rolledBackAt: null,
        notes: null,
      },
    ];
  }
  return FIXTURES[agentId];
}

function applyAction(
  deployments: Deployment[],
  depId: string,
  action: "promote" | "pause" | "rollback",
): Deployment {
  const idx = deployments.findIndex((d) => d.id === depId);
  if (idx === -1) throw new Error(`deployment ${depId} not found`);
  const target = deployments[idx];
  if (!target) throw new Error(`deployment ${depId} not found`);
  const now = new Date().toISOString();
  let next: Deployment;
  if (action === "promote") {
    next = {
      ...target,
      stage: "production",
      status: "live",
      trafficPercent: 100,
      promotedAt: now,
      pausedAt: null,
    };
    deployments[idx] = next;
    for (let i = 0; i < deployments.length; i += 1) {
      const current = deployments[i];
      if (!current) continue;
      if (i !== idx && current.status === "live") {
        deployments[i] = {
          ...current,
          status: "superseded",
          trafficPercent: 0,
        };
      }
    }
  } else if (action === "pause") {
    next = { ...target, stage: "paused", status: "paused", pausedAt: now };
    deployments[idx] = next;
  } else {
    next = {
      ...target,
      stage: "rolled_back",
      status: "rolled_back",
      trafficPercent: 0,
      rolledBackAt: now,
    };
    deployments[idx] = next;
    const prevLive = deployments.find((d) => d.status === "superseded");
    if (prevLive) {
      const i = deployments.indexOf(prevLive);
      if (i >= 0) {
        deployments[i] = { ...prevLive, status: "live", trafficPercent: 100 };
      }
    }
  }
  return next;
}

function applyRamp(
  deployments: Deployment[],
  depId: string,
  trafficPercent: number,
): Deployment {
  const idx = deployments.findIndex((d) => d.id === depId);
  if (idx === -1) throw new Error(`deployment ${depId} not found`);
  const target = deployments[idx];
  if (!target) throw new Error(`deployment ${depId} not found`);
  if (target.status !== "canary" && target.status !== "ramp") {
    throw new Error(`deployment ${depId} cannot ramp from ${target.status}`);
  }
  const next: Deployment = {
    ...target,
    stage: "ramp",
    status: "ramp",
    trafficPercent,
  };
  deployments[idx] = next;
  return next;
}

export async function listDeployments(
  agentId: string,
  opts: DeployHelperOptions = {},
): Promise<DeploymentListResponse> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture) return { items: [...seedFixtures(agentId)] };
    return {
      items: [],
      degraded_reason:
        "LOOP_CP_API_BASE_URL is required to load deployment history.",
    };
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/agents/${agentId}/deployments`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (!res.ok) throw new Error(`listDeployments failed: ${res.status}`);
  return (await res.json()) as { items: Deployment[] };
}

async function callAction(
  agentId: string,
  depId: string,
  action: "promote" | "pause" | "rollback",
  opts: DeployHelperOptions,
): Promise<Deployment> {
  const base = resolveBase(opts);
  if (!base) {
    if (!opts.allowFixture) {
      throw new Error(
        `LOOP_CP_API_BASE_URL is required to ${action} deployments`,
      );
    }
    return applyAction(seedFixtures(agentId), depId, action);
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(
    `${base}/agents/${agentId}/deployments/${depId}/${action}`,
    { method: "POST", headers: authHeaders(opts) },
  );
  if (!res.ok) throw new Error(`${action} failed: ${res.status}`);
  return (await res.json()) as Deployment;
}

export async function startCanaryDeployment(
  agentId: string,
  input: DeploymentStartInput,
  opts: DeployHelperOptions = {},
): Promise<{ deployment: Deployment; evidence_pack: EvidencePack }> {
  const base = resolveBase(opts);
  if (!base) {
    if (!opts.allowFixture) {
      throw new Error("LOOP_CP_API_BASE_URL is required to start deployments");
    }
    const now = new Date().toISOString();
    const stage = input.stage ?? "canary";
    const deployment: Deployment = {
      id: `dep_${Math.random().toString(36).slice(2, 10)}`,
      agentId,
      versionId: input.version_id ?? "draft-candidate",
      changePackageId: input.change_package_id,
      evidencePackId: `ep_${Math.random().toString(36).slice(2, 10)}`,
      stage,
      status: stage,
      trafficPercent: stage === "shadow" ? 0 : (input.traffic_percent ?? 5),
      channelScope: input.channel_scope ?? [],
      regionScope: input.region_scope ?? [],
      segmentScope: input.segment_scope ?? [],
      holdTimeMinutes: input.hold_time_minutes ?? 30,
      autoRollbackThresholds: input.auto_rollback_thresholds ?? {},
      createdAt: now,
      promotedAt: null,
      pausedAt: null,
      rolledBackAt: null,
      notes: input.notes ?? null,
    };
    return {
      deployment,
      evidence_pack: {
        id: deployment.evidencePackId ?? "ep_local",
        workspace_id: "",
        agent_id: agentId,
        version_id: deployment.versionId,
        deployment_id: deployment.id,
        change_package_id: input.change_package_id,
        version_manifest: {},
        behavior_diff_ref: "change_package.semantic_diff",
        tool_permission_diff_ref: "change_package.tool_changes",
        knowledge_diff_ref: "change_package.knowledge_changes",
        memory_policy_ref: "change_package.memory_changes",
        channel_deployment_plan_ref: "deployment.channelScope",
        eval_results_ref: "evals/not-run",
        approval_records_ref: "change_package.required_approvals",
        canary_results_ref: `deployment/${deployment.id}/${stage}`,
        rollback_plan_ref: "last-known-safe",
        audit_log_ref: `deployment/${deployment.id}/audit`,
        created_at: now,
        export_formats: ["pdf", "json", "csv", "grc_integration", "api"],
      },
    };
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/agents/${agentId}/deployments/start`, {
    method: "POST",
    headers: authHeaders(opts),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`start deployment failed: ${res.status}`);
  return (await res.json()) as {
    deployment: Deployment;
    evidence_pack: EvidencePack;
  };
}

export async function promoteDeployment(
  agentId: string,
  depId: string,
  opts: DeployHelperOptions = {},
): Promise<Deployment> {
  return callAction(agentId, depId, "promote", opts);
}

export async function rampDeployment(
  agentId: string,
  depId: string,
  trafficPercent: number,
  opts: DeployHelperOptions = {},
): Promise<Deployment> {
  const base = resolveBase(opts);
  if (!base) {
    if (!opts.allowFixture) {
      throw new Error("LOOP_CP_API_BASE_URL is required to ramp deployments");
    }
    return applyRamp(seedFixtures(agentId), depId, trafficPercent);
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(
    `${base}/agents/${agentId}/deployments/${depId}/ramp`,
    {
      method: "POST",
      headers: authHeaders(opts),
      body: JSON.stringify({ traffic_percent: trafficPercent }),
    },
  );
  if (!res.ok) throw new Error(`ramp failed: ${res.status}`);
  return (await res.json()) as Deployment;
}

export async function pauseDeployment(
  agentId: string,
  depId: string,
  opts: DeployHelperOptions = {},
): Promise<Deployment> {
  return callAction(agentId, depId, "pause", opts);
}

export async function rollbackDeployment(
  agentId: string,
  depId: string,
  opts: DeployHelperOptions = {},
): Promise<Deployment> {
  return callAction(agentId, depId, "rollback", opts);
}

export function findCurrentCanary(
  deployments: Deployment[],
): Deployment | null {
  return deployments.find((d) => d.status === "canary") ?? null;
}

export function findLiveDeployment(
  deployments: Deployment[],
): Deployment | null {
  return deployments.find((d) => d.status === "live") ?? null;
}

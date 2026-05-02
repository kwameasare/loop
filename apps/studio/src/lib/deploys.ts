/**
 * S270: Deploys helpers for the agent-detail "Deploys" tab.
 *
 * cp-api endpoints:
 *   GET  /v1/agents/{id}/deployments                  → { items: Deployment[] }
 *   POST /v1/agents/{id}/deployments/{dep_id}/promote → Deployment
 *   POST /v1/agents/{id}/deployments/{dep_id}/pause   → Deployment
 *   POST /v1/agents/{id}/deployments/{dep_id}/rollback → Deployment
 *
 * Without a configured base URL the helpers serve fixture data backed
 * by an in-memory store so the UI can be reviewed end-to-end.
 */

export type DeploymentStatus =
  | "pending"
  | "canary"
  | "live"
  | "paused"
  | "rolled_back"
  | "superseded";

export interface Deployment {
  id: string;
  agentId: string;
  versionId: string;
  status: DeploymentStatus;
  /** Percentage of traffic routed to this deployment (0–100). */
  trafficPercent: number;
  createdAt: string;
  promotedAt: string | null;
  pausedAt: string | null;
  rolledBackAt: string | null;
  notes: string | null;
}

export interface DeployHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
}

function resolveBase(opts: DeployHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL
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
  const now = new Date().toISOString();
  let next: Deployment;
  if (action === "promote") {
    next = {
      ...target,
      status: "live",
      trafficPercent: 100,
      promotedAt: now,
      pausedAt: null,
    };
    deployments[idx] = next;
    for (let i = 0; i < deployments.length; i += 1) {
      if (i !== idx && deployments[i].status === "live") {
        deployments[i] = {
          ...deployments[i],
          status: "superseded",
          trafficPercent: 0,
        };
      }
    }
  } else if (action === "pause") {
    next = { ...target, status: "paused", pausedAt: now };
    deployments[idx] = next;
  } else {
    next = {
      ...target,
      status: "rolled_back",
      trafficPercent: 0,
      rolledBackAt: now,
    };
    deployments[idx] = next;
    const prevLive = deployments.find((d) => d.status === "superseded");
    if (prevLive) {
      const i = deployments.indexOf(prevLive);
      deployments[i] = { ...prevLive, status: "live", trafficPercent: 100 };
    }
  }
  return next;
}

export async function listDeployments(
  agentId: string,
  opts: DeployHelperOptions = {},
): Promise<{ items: Deployment[] }> {
  const base = resolveBase(opts);
  if (!base) return { items: [...seedFixtures(agentId)] };
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

export async function promoteDeployment(
  agentId: string,
  depId: string,
  opts: DeployHelperOptions = {},
): Promise<Deployment> {
  return callAction(agentId, depId, "promote", opts);
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

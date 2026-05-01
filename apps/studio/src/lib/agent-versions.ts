/**
 * Agent-version data shapes and a thin loader the versions tab calls.
 *
 * The cp-api currently exposes ``POST /v1/agents/{id}/versions`` for
 * deploys but no GET-list endpoint and no ``config_json`` field on
 * AgentVersion (see openapi.yaml#components/schemas/AgentVersion).
 * Studio needs both to render the diff viewer, so we ship a small
 * studio-local type + fixture loader. The loader is wired so swapping
 * to a real endpoint is a one-line change once the cp-api story
 * (S560 / S561 — see Open questions on S160) lands.
 */

export type DeployState =
  | "inactive"
  | "canary"
  | "active"
  | "rolled_back";

export type EvalStatus =
  | "pending"
  | "running"
  | "passed"
  | "failed"
  | "skipped";

export interface AgentVersionDetail {
  id: string;
  agent_id: string;
  version: number;
  deploy_state: DeployState;
  deployed_at: string | null;
  eval_status: EvalStatus;
  /** Frozen JSON5/JSON config snapshot. Pretty-printed (2-space indent). */
  config_json: string;
}

export interface ListAgentVersionsResponse {
  items: AgentVersionDetail[];
  next_cursor: string | null;
}

export interface ListAgentVersionsOptions {
  fetcher?: typeof fetch;
  cursor?: string;
  pageSize?: number;
}

/**
 * Returns a fixture page of versions for the given agent. The fixture
 * is sorted newest-first (matches the eventual cp-api ordering). When
 * ``LOOP_CP_API_BASE_URL`` is set we still return the fixture today —
 * the GET endpoint isn't implemented yet — but the call site is the
 * single place to rewire when it lands.
 */
export async function listAgentVersions(
  agentId: string,
  opts: ListAgentVersionsOptions = {},
): Promise<ListAgentVersionsResponse> {
  const all = fixtureVersions(agentId);
  const pageSize = opts.pageSize ?? 5;
  const cursorIdx = opts.cursor ? Number.parseInt(opts.cursor, 10) || 0 : 0;
  const slice = all.slice(cursorIdx, cursorIdx + pageSize);
  const next = cursorIdx + pageSize < all.length
    ? String(cursorIdx + pageSize)
    : null;
  return { items: slice, next_cursor: next };
}

/**
 * Compute the prior-version diff input for a given version. Returns
 * the chronologically previous version (lower ``version`` number) or
 * null when ``target`` is the first version.
 */
export function priorVersion(
  versions: AgentVersionDetail[],
  target: AgentVersionDetail,
): AgentVersionDetail | null {
  const sorted = [...versions].sort((a, b) => a.version - b.version);
  const idx = sorted.findIndex((v) => v.id === target.id);
  if (idx <= 0) return null;
  return sorted[idx - 1];
}

function fixtureVersions(agentId: string): AgentVersionDetail[] {
  // 12 versions so pagination has something to do at pageSize=5.
  const base = (n: number) =>
    JSON.stringify(
      {
        model: n < 8 ? "gpt-4o-mini" : "gpt-4o",
        temperature: n % 3 === 0 ? 0.2 : 0.7,
        system_prompt: `You are agent v${n}.`,
        tools: n < 5 ? ["search"] : ["search", "calc"],
      },
      null,
      2,
    );
  return Array.from({ length: 12 }, (_, i) => {
    const version = 12 - i; // newest first
    return {
      id: `ver_${agentId}_${version}`,
      agent_id: agentId,
      version,
      deploy_state: version === 12 ? "active" : "inactive",
      deployed_at:
        version === 12 ? "2026-04-30T12:00:00Z" : "2026-04-29T12:00:00Z",
      eval_status: version === 12 ? "passed" : "skipped",
      config_json: base(version),
    } satisfies AgentVersionDetail;
  });
}

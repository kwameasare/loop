import {
  type Agent,
  type AgentVersion,
  type AgentVersionList,
  createCpApi,
  createCpApiFetch,
} from "@/lib/cp-api/generated";

export type AgentSummary = {
  id: string;
  name: string;
  description: string;
  slug: string;
  active_version: number | null;
  updated_at: string; // ISO 8601
  workspace_id: string;
};

export type ListAgentsResponse = {
  agents: AgentSummary[];
};

export type AgentVersionSummary = {
  id: string;
  agent_id: string;
  version: number;
  eval_status: "pending" | "running" | "passed" | "failed" | "skipped";
  deploy_state: "inactive" | "canary" | "active" | "rolled_back";
  deployed_at: string | null;
  created_at: string;
  created_by: string | null;
  code_hash: string;
  config_json: Record<string, unknown>;
};

export type ListAgentVersionsResponse = {
  versions: AgentVersionSummary[];
  next_cursor: string | null;
};

export interface ListAgentsOptions {
  fetcher?: typeof fetch;
  token?: string;
}

function cpApiBaseUrl(): string {
  const raw =
    process.env.LOOP_CP_API_BASE_URL ?? process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required to list agents");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function toAgentSummary(agent: Agent): AgentSummary {
  return {
    id: agent.id ?? "",
    name: agent.name ?? "Untitled agent",
    description: agent.description ?? "",
    slug: agent.slug ?? "",
    active_version: agent.active_version ?? null,
    updated_at: agent.created_at ?? "",
    workspace_id: agent.workspace_id ?? "",
  };
}

function toAgentVersionSummary(version: AgentVersion): AgentVersionSummary {
  return {
    id: version.id ?? "",
    agent_id: version.agent_id ?? "",
    version: version.version ?? 0,
    eval_status: version.eval_status ?? "pending",
    deploy_state: version.deploy_state ?? "inactive",
    deployed_at: version.deployed_at ?? null,
    created_at: version.created_at ?? "",
    created_by: version.created_by ?? null,
    code_hash: version.code_hash ?? "",
    config_json: version.config_json ?? {},
  };
}

function noStoreFetch(fetcher: typeof fetch): typeof fetch {
  return (input, init) => fetcher(input, { ...init, cache: "no-store" });
}

/**
 * Returns the agents visible to the current workspace.
 *
 * Studio calls the generated cp-api client rather than a fixture. The
 * control plane scopes GET /v1/agents to the active workspace derived
 * from the caller's auth context.
 */
export async function listAgents(
  opts: ListAgentsOptions = {},
): Promise<ListAgentsResponse> {
  const api = createCpApi({
    baseUrl: cpApiBaseUrl(),
    fetch: noStoreFetch(opts.fetcher ?? fetch),
    token: opts.token ?? process.env.LOOP_TOKEN,
  });
  const agents = await api.GetAgents({ body: undefined });
  return { agents: agents.map(toAgentSummary) };
}

export interface CreateAgentInput {
  name: string;
  slug: string;
  description?: string;
}

export interface CreateAgentOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

/**
 * Create a new agent in the active workspace and return the canonical
 * summary. Studio's "New agent" modal calls this from a client
 * component; the host browser's fetch carries the bearer token via
 * cp-api auth middleware.
 */
export async function createAgent(
  input: CreateAgentInput,
  opts: CreateAgentOptions = {},
): Promise<AgentSummary> {
  const api = createCpApi({
    baseUrl: opts.baseUrl ?? cpApiBaseUrl(),
    fetch: opts.fetcher ?? fetch,
    token: opts.token,
  });
  const payload = {
    name: input.name,
    slug: input.slug,
    description: input.description ?? "",
  };
  const created = await api.PostAgents({ body: payload });
  return toAgentSummary(created);
}

export interface GetAgentOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

/**
 * Fetch a single agent by id. Used by the agent detail page shell so
 * each tab segment can render the agent's name and slug without
 * hitting the wire itself (the layout caches the agent for its
 * children).
 */
export async function getAgent(
  agentId: string,
  opts: GetAgentOptions = {},
): Promise<AgentSummary> {
  const api = createCpApi({
    baseUrl: opts.baseUrl ?? cpApiBaseUrl(),
    fetch: noStoreFetch(opts.fetcher ?? fetch),
    token: opts.token ?? process.env.LOOP_TOKEN,
  });
  const agent = await api.GetAgentsByAgentId({
    agent_id: agentId,
    body: undefined,
  });
  return toAgentSummary(agent);
}

export interface ListAgentVersionsOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
  cursor?: string;
  limit?: number;
}

/**
 * Fetch a cursor page of agent versions, newest first, with the
 * config_json payload needed by Studio's version diff modal.
 */
export async function listAgentVersions(
  agentId: string,
  opts: ListAgentVersionsOptions = {},
): Promise<ListAgentVersionsResponse> {
  const fetcher = createCpApiFetch({
    baseUrl: opts.baseUrl ?? cpApiBaseUrl(),
    fetch: noStoreFetch(opts.fetcher ?? fetch),
    token: opts.token ?? process.env.LOOP_TOKEN,
  });
  const query = new URLSearchParams();
  if (opts.cursor) query.set("cursor", opts.cursor);
  if (opts.limit !== undefined) query.set("limit", String(opts.limit));
  const queryString = query.toString();
  const suffix = queryString ? `?${queryString}` : "";
  const page = await fetcher<AgentVersionList>(
    "GET",
    `/agents/${encodeURIComponent(agentId)}/versions${suffix}`,
  );
  return {
    versions: (page.items ?? []).map(toAgentVersionSummary),
    next_cursor: page.next_cursor ?? null,
  };
}

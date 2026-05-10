import { type Agent, createCpApi } from "@/lib/cp-api/generated";
import { createAuthedCpApiFetch } from "@/lib/cp-api-fetch";

export type AgentSummary = {
  id: string;
  name: string;
  description: string;
  slug: string;
  active_version: number | null;
  object_state:
    | "draft"
    | "saved"
    | "staged"
    | "canary"
    | "production"
    | "rolled_back"
    | "archived";
  state_reason: string;
  state_evidence_ref: string;
  updated_at: string; // ISO 8601
  workspace_id: string;
  owner_user_id?: string | null;
  backup_owner_user_id?: string | null;
  environment?: string;
  health_status?: string;
  open_issue_count?: number;
  open_issue_sources?: string[];
  commitment_document_id?: string | null;
  commitment_status?: string | null;
};

export type ListAgentsResponse = {
  agents: AgentSummary[];
};

export interface ListAgentsOptions {
  fetcher?: typeof fetch;
  token?: string;
  workspaceId?: string | null | undefined;
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
  const stateful = agent as Agent & {
    object_state?: AgentSummary["object_state"];
    state_reason?: string;
    state_evidence_ref?: string;
    owner_user_id?: string | null;
    backup_owner_user_id?: string | null;
    environment?: string;
    health_status?: string;
    open_issue_count?: number;
    open_issue_sources?: string[];
    commitment_document_id?: string | null;
    commitment_status?: string | null;
  };
  const fallbackState: AgentSummary["object_state"] =
    agent.active_version !== null && agent.active_version !== undefined
      ? "production"
      : "draft";
  return {
    id: agent.id ?? "",
    name: agent.name ?? "Untitled agent",
    description: agent.description ?? "",
    slug: agent.slug ?? "",
    active_version: agent.active_version ?? null,
    object_state: stateful.object_state ?? fallbackState,
    state_reason:
      stateful.state_reason ??
      (fallbackState === "production"
        ? "Agent has an active production version."
        : "Agent has no active production version."),
    state_evidence_ref:
      stateful.state_evidence_ref ??
      (fallbackState === "production" ? "agent.active_version" : "agent.draft"),
    updated_at: agent.created_at ?? "",
    workspace_id: agent.workspace_id ?? "",
    owner_user_id: stateful.owner_user_id ?? null,
    backup_owner_user_id: stateful.backup_owner_user_id ?? null,
    environment: stateful.environment ?? fallbackState,
    health_status:
      stateful.health_status ??
      (fallbackState === "production" ? "watching" : "drafting"),
    open_issue_count: stateful.open_issue_count ?? 0,
    open_issue_sources: stateful.open_issue_sources ?? [],
    commitment_document_id: stateful.commitment_document_id ?? null,
    commitment_status: stateful.commitment_status ?? null,
  };
}

function noStoreFetch(fetcher: typeof fetch): typeof fetch {
  return (input, init) => fetcher(input, { ...init, cache: "no-store" });
}

/**
 * Inject the selected ``X-Loop-Workspace-Id`` when the caller has
 * resolved workspace context. ``LOOP_DEFAULT_WORKSPACE_ID`` remains a
 * local-dev fallback, but production pages should pass an explicit
 * workspace id before requesting workspace-scoped agent data.
 */
function withWorkspaceHeader(
  fetcher: typeof fetch,
  workspaceId?: string | null,
): typeof fetch {
  return (input, init) => {
    const resolvedWorkspaceId =
      workspaceId?.trim() || process.env.LOOP_DEFAULT_WORKSPACE_ID;
    if (!resolvedWorkspaceId) return fetcher(input, init);
    const headers = new Headers(init?.headers);
    if (!headers.has("x-loop-workspace-id")) {
      headers.set("x-loop-workspace-id", resolvedWorkspaceId);
    }
    return fetcher(input, { ...init, headers });
  };
}

function cpApiFetch(opts: {
  fetcher?: typeof fetch;
  baseUrl: string;
  workspaceId?: string | null | undefined;
}): typeof fetch {
  const authed = createAuthedCpApiFetch({
    ...(opts.fetcher ? { fetcher: opts.fetcher } : {}),
    // refreshSessionToken appends /v1/auth/refresh; pass origin-ish base.
    refreshBaseUrl: opts.baseUrl.replace(/\/v1$/, ""),
  });
  return noStoreFetch(withWorkspaceHeader(authed, opts.workspaceId));
}

function createApiClient(opts: {
  baseUrl: string;
  fetcher: typeof fetch | undefined;
  token: string | undefined;
  workspaceId?: string | null | undefined;
}) {
  return createCpApi({
    baseUrl: opts.baseUrl,
    fetch: cpApiFetch(
      opts.fetcher
        ? {
            fetcher: opts.fetcher,
            baseUrl: opts.baseUrl,
            workspaceId: opts.workspaceId,
          }
        : { baseUrl: opts.baseUrl, workspaceId: opts.workspaceId },
    ),
    ...(opts.token !== undefined ? { token: opts.token } : {}),
  });
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
  const baseUrl = cpApiBaseUrl();
  const token = opts.token ?? process.env.LOOP_TOKEN;
  const api = createApiClient({
    baseUrl,
    fetcher: opts.fetcher,
    token,
    workspaceId: opts.workspaceId,
  });
  const agents = await api.GetAgents({ body: undefined });
  const items: Agent[] = Array.isArray(agents)
    ? (agents as Agent[])
    : (agents.items ?? []);
  return { agents: items.map(toAgentSummary) };
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
  workspaceId?: string | null | undefined;
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
  const baseUrl = opts.baseUrl ?? cpApiBaseUrl();
  const api = createApiClient({
    baseUrl,
    fetcher: opts.fetcher,
    token: opts.token,
    workspaceId: opts.workspaceId,
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
  const baseUrl = opts.baseUrl ?? cpApiBaseUrl();
  const token = opts.token ?? process.env.LOOP_TOKEN;
  const api = createApiClient({ baseUrl, fetcher: opts.fetcher, token });
  const agent = await api.GetAgentsByAgentId({
    agent_id: agentId,
    body: undefined,
  });
  return toAgentSummary(agent);
}

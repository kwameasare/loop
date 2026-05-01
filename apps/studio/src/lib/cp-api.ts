import { type Agent, createCpApi } from "@/lib/cp-api/generated";

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

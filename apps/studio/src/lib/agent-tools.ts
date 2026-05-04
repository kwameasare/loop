/**
 * P0.3: cp-api client for agent tool catalog.
 *
 * Reads ``GET /v1/agents/{agent_id}/tools`` (per-agent binding) which
 * is blocked on cp-api PR — the underlying ``mcp_marketplace.py``
 * service module exists but no FastAPI shim is mounted yet. Until
 * then the call returns an empty catalog so the page renders cleanly
 * and lights up automatically when the route lands.
 */

export type AgentToolKind = "mcp" | "http";

export interface AgentTool {
  id: string;
  name: string;
  kind: AgentToolKind;
  /** Human-readable description, optional. */
  description?: string;
  /** Origin server URL (MCP base URL or HTTP server root). */
  source?: string;
}

export interface AgentToolsClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) throw new Error("LOOP_CP_API_BASE_URL is required for tools calls");
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

export async function listAgentTools(
  agent_id: string,
  opts: AgentToolsClientOptions = {},
): Promise<AgentTool[]> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${cpApiBaseUrl(opts.baseUrl)}/agents/${encodeURIComponent(
    agent_id,
  )}/tools`;
  const res = await fetcher(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`cp-api GET agent tools -> ${res.status}`);
  const body = (await res.json()) as { items?: AgentTool[] };
  return body.items ?? [];
}

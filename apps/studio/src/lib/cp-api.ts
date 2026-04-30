/**
 * cp-api -- thin client for the Loop control-plane HTTP API.
 *
 * S0 ships a stub: the studio renders against an in-memory fixture so we
 * can iterate on UI before the live API stabilises. Once cp-api goes RC
 * (E5/S023) flip `LOOP_CP_API_BASE_URL` and the same call signatures
 * carry over.
 *
 * Wire shapes mirror packages/control-plane response payloads. They are
 * intentionally narrow -- studio pages should not depend on internal
 * fields.
 */

export type AgentSummary = {
  id: string;
  name: string;
  model: string;
  description: string;
  status: "active" | "draft" | "archived";
  updated_at: string; // ISO 8601
};

export type ListAgentsResponse = {
  agents: AgentSummary[];
};

const FIXTURE: AgentSummary[] = [
  {
    id: "agt_support",
    name: "Support",
    model: "gpt-4o-mini",
    description: "Customer-support agent with KB grounding.",
    status: "active",
    updated_at: "2026-04-29T12:00:00Z",
  },
  {
    id: "agt_qa",
    name: "QA Bot",
    model: "claude-3-5-haiku",
    description: "Internal Q&A over the engineering handbook.",
    status: "draft",
    updated_at: "2026-04-28T09:30:00Z",
  },
];

/**
 * Returns the agents visible to the current workspace.
 *
 * In production this issues GET /v1/agents against cp-api with the
 * caller's session cookie attached. The stub just resolves the fixture
 * so studio routing/rendering can be exercised offline.
 */
export async function listAgents(): Promise<ListAgentsResponse> {
  const baseUrl = process.env.LOOP_CP_API_BASE_URL;
  if (!baseUrl) {
    return { agents: FIXTURE };
  }
  const res = await fetch(`${baseUrl}/v1/agents`, {
    cache: "no-store",
    headers: { accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`cp-api list agents failed: ${res.status}`);
  }
  return (await res.json()) as ListAgentsResponse;
}

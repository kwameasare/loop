import { getAgent, type AgentSummary } from "@/lib/cp-api";

export interface AgentDetailData {
  agent: AgentSummary;
  degradedReason?: string;
}

function slugFromAgentId(agentId: string): string {
  return (
    agentId
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 40) || "agent"
  );
}

function fallbackAgent(agentId: string): AgentSummary {
  return {
    id: agentId,
    name:
      slugFromAgentId(agentId)
        .split("-")
        .filter(Boolean)
        .map((part) => part[0]?.toUpperCase() + part.slice(1))
        .join(" ") || "Unavailable agent",
    description: "Live agent data is unavailable for this request.",
    slug: slugFromAgentId(agentId),
    active_version: null,
    updated_at: "1970-01-01T00:00:00Z",
    workspace_id: "unavailable",
  };
}

export async function getAgentDetailData(
  agentId: string,
): Promise<AgentDetailData> {
  try {
    return { agent: await getAgent(agentId) };
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "cp-api did not return this agent.";
    return {
      agent: fallbackAgent(agentId),
      degradedReason: `Live agent data is unavailable for this request. Evidence: ${message}`,
    };
  }
}

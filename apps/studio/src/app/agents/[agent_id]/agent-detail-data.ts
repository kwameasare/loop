import { getAgent, type AgentSummary } from "@/lib/cp-api";
import { targetUxFixtures } from "@/lib/target-ux";

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
  const fixture =
    targetUxFixtures.agents.find((candidate) => candidate.id === agentId) ??
    targetUxFixtures.agents[0]!;
  return {
    id: agentId,
    name: fixture.name,
    description: fixture.purpose,
    slug: slugFromAgentId(agentId),
    active_version: 24,
    updated_at: targetUxFixtures.evals[0]?.lastRun ?? "2026-05-06T08:30:00Z",
    workspace_id: targetUxFixtures.workspace.id,
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
      degradedReason: `Showing cached target fixture because live agent data is unavailable. Evidence: ${message}`,
    };
  }
}

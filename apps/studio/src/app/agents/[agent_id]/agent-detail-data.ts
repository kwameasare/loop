import { getAgent, type AgentSummary } from "@/lib/cp-api";

export interface AgentDetailData {
  agent: AgentSummary;
  degradedReason?: string;
}

export function agentProductionLabel(agent: AgentSummary): string {
  return agent.active_version !== null
    ? `v${agent.active_version}`
    : "not live";
}

export function agentStateLabel(agent: AgentSummary): string {
  return agent.object_state.replace(/_/g, " ");
}

export function agentStateSentence(agent: AgentSummary): string {
  const subject = agent.name || agent.id;
  const production = agentProductionLabel(agent);
  const state = agentStateLabel(agent);
  const reason = agent.state_reason.trim();
  const evidence = agent.state_evidence_ref.trim();
  return [
    `You are working on agent \`${subject}\`.`,
    `Current state is ${state}.`,
    `Production is ${production}.`,
    reason ? reason : "No additional state reason is available.",
    evidence
      ? `Evidence: ${evidence}.`
      : "No state evidence reference is available.",
  ].join(" ");
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
    object_state: "draft",
    state_reason: "Live agent data is unavailable.",
    state_evidence_ref: "agent.unavailable",
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

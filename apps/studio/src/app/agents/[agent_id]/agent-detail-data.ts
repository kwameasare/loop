import { getAgent, type AgentSummary } from "@/lib/cp-api";
import { getCpAccessToken } from "@/lib/server/session";
import type {
  AgentBranch,
  AgentChangeSet,
  AgentReleaseCandidate,
  AgentWorkflow,
} from "@/lib/agent-workflow";

export interface AgentDetailData {
  agent: AgentSummary;
  degradedReason?: string;
}

export interface AgentTopbarFact {
  id:
    | "branch"
    | "draft"
    | "production"
    | "environment"
    | "health"
    | "lastDeploy"
    | "openIssues";
  label: string;
  value: string;
  evidence: string;
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

function latestByUpdatedAt<T extends { updated_at: string }>(
  items: T[] | undefined,
): T | undefined {
  return [...(items ?? [])].sort((a, b) =>
    b.updated_at.localeCompare(a.updated_at),
  )[0];
}

function branchLabel(branch: AgentBranch | undefined): string {
  if (!branch) return "No branch loaded";
  return `${branch.name} · ${branch.status.replaceAll("_", " ")}`;
}

function draftChangeLabel(changeSet: AgentChangeSet | undefined): string {
  if (!changeSet) return "No Change Set loaded";
  return `${changeSet.name} · ${changeSet.status.replaceAll("_", " ")}`;
}

function releaseCandidateIssues(
  releaseCandidates: AgentReleaseCandidate[] | undefined,
): number {
  return (releaseCandidates ?? []).reduce((count, candidate) => {
    const failedGates = candidate.readiness.filter(
      (gate) => gate.status === "failed",
    ).length;
    const blockedCandidate = candidate.status === "blocked" ? 1 : 0;
    return count + failedGates + blockedCandidate;
  }, 0);
}

export function agentWorkbenchTopbarFacts(
  agent: AgentSummary,
  workflow?: AgentWorkflow | undefined,
): AgentTopbarFact[] {
  const branch = latestByUpdatedAt(workflow?.branches);
  const changeSet = latestByUpdatedAt(workflow?.change_sets);
  const releaseCandidateIssueCount = releaseCandidateIssues(
    workflow?.release_candidates,
  );
  const draftIssueCount = changeSet
    ? changeSet.status === "abandoned"
      ? 1
      : changeSet.status === "draft" || changeSet.status === "ready_for_tests"
        ? 1
        : 0
    : 0;
  const openIssueCount = releaseCandidateIssueCount + draftIssueCount;
  const health =
    openIssueCount > 0
      ? "Needs attention"
      : agent.object_state === "production" || agent.object_state === "canary"
        ? "Watching"
        : agent.object_state === "draft"
          ? "Drafting"
          : agentStateLabel(agent);

  return [
    {
      id: "branch",
      label: "Branch",
      value: branchLabel(branch),
      evidence: branch ? `branch/${branch.id}` : "workflow.branches.empty",
    },
    {
      id: "draft",
      label: "Draft change",
      value: draftChangeLabel(changeSet),
      evidence: changeSet
        ? `change-set/${changeSet.id}`
        : "workflow.change_sets.empty",
    },
    {
      id: "production",
      label: "Production",
      value: agentProductionLabel(agent),
      evidence: agent.active_version !== null ? "agent.active_version" : "agent",
    },
    {
      id: "environment",
      label: "Environment",
      value: agentStateLabel(agent),
      evidence: "agent.object_state",
    },
    {
      id: "health",
      label: "Health",
      value: health,
      evidence:
        openIssueCount > 0
          ? "workflow.open_issues"
          : agent.state_evidence_ref || "agent.state",
    },
    {
      id: "lastDeploy",
      label: "Last deploy",
      value:
        agent.active_version !== null
          ? `Active ${agentProductionLabel(agent)}`
          : "No deploy loaded",
      evidence:
        agent.active_version !== null ? "agent.active_version" : "deploy.empty",
    },
    {
      id: "openIssues",
      label: "Open issues",
      value: workflow ? String(openIssueCount) : "Workflow unavailable",
      evidence: workflow ? "workflow.state" : "workflow.unavailable",
    },
  ];
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
  const token = getCpAccessToken();
  const auth = token ? { token } : {};
  try {
    return { agent: await getAgent(agentId, auth) };
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

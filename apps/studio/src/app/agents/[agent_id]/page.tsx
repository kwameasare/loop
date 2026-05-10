/**
 * S159: Agent overview tab -- description, model, last-deploy summary,
 * and edit-description modal.
 */
import {
  AgentOverview,
  type DeploySummary,
} from "@/components/agents/agent-overview";
import {
  buildLocalCommitmentDocument,
  fetchCurrentCommitment,
} from "@/lib/agent-commitment";
import { listDeployments, type Deployment } from "@/lib/deploys";
import { getAgentDetailData } from "./agent-detail-data";

interface AgentOverviewPageProps {
  params: { agent_id: string };
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function deployedAt(deployment: Deployment): string {
  return deployment.promotedAt ?? deployment.createdAt;
}

function latestDeployment(deployments: Deployment[]): Deployment | null {
  return (
    [...deployments].sort(
      (left, right) =>
        Date.parse(deployedAt(right)) - Date.parse(deployedAt(left)),
    )[0] ?? null
  );
}

function versionNumberFromDeployment(deployment: Deployment): number | null {
  const match = deployment.versionId.match(/(\d+)$/);
  return match ? Number.parseInt(match[1]!, 10) : null;
}

function deploySummaryFromHistory(
  deployments: Deployment[],
  unavailableReason?: string,
): DeploySummary {
  if (unavailableReason) {
    return {
      deployed_at: null,
      version: null,
      status: null,
      unavailableReason,
    };
  }
  const latest = latestDeployment(deployments);
  if (!latest) return { deployed_at: null, version: null, status: null };
  return {
    deployed_at: deployedAt(latest),
    version: versionNumberFromDeployment(latest),
    status: latest.status,
  };
}

export default async function AgentOverviewPage({
  params,
}: AgentOverviewPageProps) {
  const { agent, degradedReason } = await getAgentDetailData(params.agent_id);
  let commitment = buildLocalCommitmentDocument(params.agent_id);
  let commitmentDegradedReason: string | undefined;
  try {
    commitment = await fetchCurrentCommitment(params.agent_id);
  } catch (error) {
    commitment = buildLocalCommitmentDocument(params.agent_id);
    commitmentDegradedReason = errorMessage(
      error,
      "Could not load the current Commitment Document.",
    );
  }
  let deployments: Deployment[] = [];
  let deploymentsDegradedReason: string | undefined;
  try {
    const result = await listDeployments(params.agent_id);
    deployments = result.items;
    deploymentsDegradedReason = result.degraded_reason;
  } catch (error) {
    deploymentsDegradedReason = errorMessage(
      error,
      "Could not load deployment history.",
    );
  }
  const combinedDegradedReason = [
    degradedReason,
    commitmentDegradedReason,
    deploymentsDegradedReason,
  ]
    .filter(Boolean)
    .join(" ");
  const lastDeploy = deploySummaryFromHistory(
    deployments,
    deploymentsDegradedReason,
  );

  return (
    <AgentOverview
      id={agent.id}
      name={agent.name}
      slug={agent.slug}
      description={agent.description}
      model=""
      activeVersion={agent.active_version}
      objectState={agent.object_state}
      stateReason={agent.state_reason}
      stateEvidenceRef={agent.state_evidence_ref}
      updatedAt={agent.updated_at}
      lastDeploy={lastDeploy}
      dataState={combinedDegradedReason ? "degraded" : "live"}
      degradedReason={combinedDegradedReason || undefined}
      commitment={commitment}
    />
  );
}

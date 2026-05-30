/**
 * S159: Agent overview tab -- description, model, last-deploy summary,
 * and edit-description modal.
 */
import {
  AgentOverview,
  type DeploySummary,
} from "@/components/agents/agent-overview";
import { AgentTestTurn } from "@/components/agents/agent-test-turn";
import {
  fetchCurrentCommitment,
  type CommitmentDocument,
} from "@/lib/agent-commitment";
import {
  fetchCurrentChangePackage,
  type ChangePackage,
} from "@/lib/change-package";
import {
  listChannelBindings,
  type ChannelBinding,
} from "@/lib/channel-bindings";
import { listDeployments, type Deployment } from "@/lib/deploys";
import { listEvalSuites, type EvalSuite } from "@/lib/evals";
import { fetchAgentHandoff, type AgentHandoffModel } from "@/lib/agent-handoff";
import {
  getAgentIntake,
  type AgentIntakeRecord,
} from "@/lib/agent-intake";
import { listAgentWorkflow, type AgentWorkflow } from "@/lib/agent-workflow";
import { listKbDocuments, type KbDocument } from "@/lib/kb";
import { listMemoryPolicies, type MemoryPolicy } from "@/lib/memory-policies";
import { listToolContracts, type ToolContract } from "@/lib/tool-contracts";
import { searchTraces, type TraceSummary } from "@/lib/traces";
import { getAgentDetailData } from "./agent-detail-data";

interface AgentOverviewPageProps {
  params: { agent_id: string };
  searchParams?: { intake?: string | string[] | undefined } | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
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
  searchParams,
}: AgentOverviewPageProps) {
  const { agent, degradedReason } = await getAgentDetailData(params.agent_id);
  const focusedIntakeId = firstParam(searchParams?.intake);
  let commitment: CommitmentDocument | undefined;
  let commitmentDegradedReason: string | undefined;
  try {
    commitment = await fetchCurrentCommitment(params.agent_id);
  } catch (error) {
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
  let channelBindings: ChannelBinding[] = [];
  let channelsDegradedReason: string | undefined;
  try {
    const result = await listChannelBindings(params.agent_id);
    channelBindings = result.items;
    channelsDegradedReason = result.degraded_reason;
  } catch (error) {
    channelsDegradedReason = errorMessage(
      error,
      "Could not load channel bindings.",
    );
  }
  let toolContracts: ToolContract[] = [];
  let toolsDegradedReason: string | undefined;
  try {
    const result = await listToolContracts(params.agent_id);
    toolContracts = result.items;
  } catch (error) {
    toolsDegradedReason = errorMessage(error, "Could not load tool contracts.");
  }
  let memoryPolicies: MemoryPolicy[] = [];
  let memoryDegradedReason: string | undefined;
  try {
    const result = await listMemoryPolicies(params.agent_id);
    memoryPolicies = result.items;
  } catch (error) {
    memoryDegradedReason = errorMessage(
      error,
      "Could not load memory policies.",
    );
  }
  let evalSuites: EvalSuite[] = [];
  let evalsDegradedReason: string | undefined;
  if (!agent.workspace_id || agent.workspace_id === "unavailable") {
    evalsDegradedReason =
      "Workspace context is required before loading eval suites.";
  } else {
    try {
      const result = await listEvalSuites({ workspaceId: agent.workspace_id });
      evalSuites = result.items.filter(
        (suite) => suite.agentId === params.agent_id,
      );
      evalsDegradedReason = result.degraded_reason;
    } catch (error) {
      evalsDegradedReason = errorMessage(error, "Could not load eval suites.");
    }
  }
  let knowledgeDocuments: KbDocument[] = [];
  let knowledgeDegradedReason: string | undefined;
  try {
    const result = await listKbDocuments(params.agent_id);
    knowledgeDocuments = result.items;
    knowledgeDegradedReason = result.degraded_reason;
  } catch (error) {
    knowledgeDegradedReason = errorMessage(
      error,
      "Could not load knowledge documents.",
    );
  }
  let changePackage: ChangePackage | undefined;
  let changePackageDegradedReason: string | undefined;
  try {
    changePackage =
      (await fetchCurrentChangePackage(params.agent_id)).item ?? undefined;
  } catch (error) {
    changePackageDegradedReason = errorMessage(
      error,
      "Could not load the current Change Package.",
    );
  }
  let traceSummaries: TraceSummary[] = [];
  let tracesDegradedReason: string | undefined;
  if (!agent.workspace_id || agent.workspace_id === "unavailable") {
    tracesDegradedReason =
      "Workspace context is unavailable, so Studio cannot request agent-scoped trace evidence.";
  } else {
    try {
      const result = await searchTraces(agent.workspace_id, {
        agent_id: params.agent_id,
        page_size: 10,
      });
      traceSummaries = result.traces;
    } catch (error) {
      tracesDegradedReason = errorMessage(
        error,
        "Could not load agent traces.",
      );
    }
  }
  let handoffModel: AgentHandoffModel | undefined;
  let handoffDegradedReason: string | undefined;
  try {
    handoffModel = await fetchAgentHandoff(params.agent_id);
  } catch (error) {
    handoffDegradedReason = errorMessage(
      error,
      "Could not load agent handoff history.",
    );
  }
  let intakeRecord: AgentIntakeRecord | undefined;
  let intakeDegradedReason: string | undefined;
  if (focusedIntakeId) {
    if (!agent.workspace_id || agent.workspace_id === "unavailable") {
      intakeDegradedReason =
        "Workspace context is required before loading the creation intake record.";
    } else {
      try {
        intakeRecord = await getAgentIntake(agent.workspace_id, focusedIntakeId);
        if (intakeRecord.agent_id !== params.agent_id) {
          intakeDegradedReason = `Intake ${focusedIntakeId} belongs to agent ${intakeRecord.agent_id}, not ${params.agent_id}.`;
          intakeRecord = undefined;
        }
      } catch (error) {
        intakeDegradedReason = errorMessage(
          error,
          "Could not load the creation intake record.",
        );
      }
    }
  }
  let workflow: AgentWorkflow | undefined;
  let workflowDegradedReason: string | undefined;
  try {
    workflow = await listAgentWorkflow(params.agent_id);
    workflowDegradedReason = workflow.degraded_reason;
  } catch (error) {
    workflowDegradedReason = errorMessage(
      error,
      "Could not load agent release workflow.",
    );
  }
  const combinedDegradedReason = [
    degradedReason,
    commitmentDegradedReason,
    deploymentsDegradedReason,
    channelsDegradedReason,
    toolsDegradedReason,
    memoryDegradedReason,
    evalsDegradedReason,
    knowledgeDegradedReason,
    changePackageDegradedReason,
    tracesDegradedReason,
    handoffDegradedReason,
    intakeDegradedReason,
    workflowDegradedReason,
  ]
    .filter(Boolean)
    .join(" ");
  const lastDeploy = deploySummaryFromHistory(
    deployments,
    deploymentsDegradedReason,
  );

  return (
    <div className="flex flex-col gap-4">
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
        channelBindings={channelBindings}
        channelsDegradedReason={channelsDegradedReason}
        toolContracts={toolContracts}
        toolsDegradedReason={toolsDegradedReason}
        memoryPolicies={memoryPolicies}
        memoryDegradedReason={memoryDegradedReason}
        evalSuites={evalSuites}
        evalsDegradedReason={evalsDegradedReason}
        knowledgeDocuments={knowledgeDocuments}
        knowledgeDegradedReason={knowledgeDegradedReason}
        changePackage={changePackage}
        changePackageDegradedReason={changePackageDegradedReason}
        traceSummaries={traceSummaries}
        tracesDegradedReason={tracesDegradedReason}
        handoffModel={handoffModel}
        handoffDegradedReason={handoffDegradedReason}
        focusedIntakeId={focusedIntakeId}
        intakeRecord={intakeRecord}
        intakeDegradedReason={intakeDegradedReason}
        workflow={workflow}
        workflowDegradedReason={workflowDegradedReason}
        commitment={commitment}
      />
      <div className="mx-auto w-full max-w-7xl px-4 lg:px-6">
        <AgentTestTurn agentId={agent.id} />
      </div>
    </div>
  );
}

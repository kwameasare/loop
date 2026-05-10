import { DeployTimeline } from "@/components/agents/deploy-timeline";
import { ChangePackagePanel } from "@/components/deploy";
import {
  buildLocalChangePackage,
  fetchCurrentChangePackage,
} from "@/lib/change-package";
import { listDeployments, listEvidencePacks } from "@/lib/deploys";

export const dynamic = "force-dynamic";

interface AgentDeploysPageProps {
  params: { agent_id: string };
}

export default async function AgentDeploysPage({
  params,
}: AgentDeploysPageProps) {
  let deployments: Awaited<ReturnType<typeof listDeployments>>["items"] = [];
  let deploymentsDegradedReason: string | undefined;
  try {
    const result = await listDeployments(params.agent_id);
    deployments = result.items;
    deploymentsDegradedReason = result.degraded_reason;
  } catch (error) {
    deployments = [];
    deploymentsDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load deployment history.";
  }

  let evidencePacks: Awaited<ReturnType<typeof listEvidencePacks>>["items"] =
    [];
  let evidencePacksDegradedReason: string | undefined;
  try {
    const result = await listEvidencePacks(params.agent_id);
    evidencePacks = result.items;
    evidencePacksDegradedReason = result.degraded_reason;
  } catch (error) {
    evidencePacks = [];
    evidencePacksDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load evidence packs.";
  }

  let changePackage = buildLocalChangePackage(params.agent_id);
  let changePackageDegradedReason: string | undefined;
  try {
    changePackage =
      (await fetchCurrentChangePackage(params.agent_id)).item ?? changePackage;
  } catch (error) {
    changePackage = buildLocalChangePackage(params.agent_id);
    changePackageDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load the current Change Package.";
  }

  return (
    <div className="space-y-6" data-testid="agent-deploys">
      <ChangePackagePanel
        agentId={params.agent_id}
        initialPackage={changePackage}
        degradedReason={changePackageDegradedReason}
      />
      <DeployTimeline
        agentId={params.agent_id}
        approvedChangePackage={
          changePackage.status === "approved" ||
          changePackage.status === "deployable"
            ? changePackage
            : null
        }
        initialDeployments={deployments}
        initialEvidencePacks={evidencePacks}
        degradedReason={
          deploymentsDegradedReason ?? evidencePacksDegradedReason
        }
      />
    </div>
  );
}

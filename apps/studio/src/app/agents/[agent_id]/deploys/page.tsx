import { DeployTimeline } from "@/components/agents/deploy-timeline";
import { ChangePackagePanel } from "@/components/deploy";
import {
  buildLocalChangePackage,
  fetchCurrentChangePackage,
} from "@/lib/change-package";
import { listDeployments } from "@/lib/deploys";

export const dynamic = "force-dynamic";

interface AgentDeploysPageProps {
  params: { agent_id: string };
}

export default async function AgentDeploysPage({
  params,
}: AgentDeploysPageProps) {
  let deployments: Awaited<ReturnType<typeof listDeployments>>["items"] = [];
  try {
    deployments = (await listDeployments(params.agent_id)).items;
  } catch {
    deployments = [];
  }

  let changePackage = buildLocalChangePackage(params.agent_id);
  try {
    changePackage =
      (await fetchCurrentChangePackage(params.agent_id)).item ?? changePackage;
  } catch {
    changePackage = buildLocalChangePackage(params.agent_id);
  }

  return (
    <div className="space-y-6" data-testid="agent-deploys">
      <ChangePackagePanel
        agentId={params.agent_id}
        initialPackage={changePackage}
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
      />
    </div>
  );
}

import { DeployTimeline } from "@/components/agents/deploy-timeline";
import { ChangePackagePanel } from "@/components/deploy";
import {
  fetchCurrentChangePackage,
  type ChangePackage,
} from "@/lib/change-package";
import { listDeployments, listEvidencePacks } from "@/lib/deploys";
import { getCpAuthOptions } from "@/lib/server/session";

export const dynamic = "force-dynamic";

interface AgentDeploysPageProps {
  params: { agent_id: string };
  searchParams?:
    | {
        change_package_id?: string | string[] | undefined;
        deployment_id?: string | string[] | undefined;
        change_set?: string | string[] | undefined;
        panel?: string | string[] | undefined;
      }
    | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AgentDeploysPage({
  params,
  searchParams,
}: AgentDeploysPageProps) {
  const authOptions = getCpAuthOptions();
  let deployments: Awaited<ReturnType<typeof listDeployments>>["items"] = [];
  let deploymentsDegradedReason: string | undefined;
  try {
    const result = await listDeployments(params.agent_id, authOptions);
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
    const result = await listEvidencePacks(params.agent_id, authOptions);
    evidencePacks = result.items;
    evidencePacksDegradedReason = result.degraded_reason;
  } catch (error) {
    evidencePacks = [];
    evidencePacksDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load evidence packs.";
  }

  let changePackage: ChangePackage | null = null;
  let changePackageDegradedReason: string | undefined;
  try {
    changePackage = (await fetchCurrentChangePackage(params.agent_id, authOptions))
      .item;
  } catch (error) {
    changePackageDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load the current Change Package.";
  }

  return (
    <div className="space-y-6" data-testid="agent-deploys">
      {firstParam(searchParams?.change_set) ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-4 text-sm text-info"
          data-testid="deploys-focused-change-set"
        >
          <p className="font-medium">Opened from co-builder change set.</p>
          <p className="mt-1 font-mono text-xs">
            {firstParam(searchParams?.change_set)}
          </p>
          <p className="mt-2 text-xs">
            Generate or refresh the Change Package below before promotion.
          </p>
        </section>
      ) : null}
      <ChangePackagePanel
        agentId={params.agent_id}
        focusedPanel={firstParam(searchParams?.panel)}
        initialPackage={changePackage}
        focusedChangePackageId={firstParam(searchParams?.change_package_id)}
        degradedReason={changePackageDegradedReason}
      />
      <DeployTimeline
        agentId={params.agent_id}
        focusedPanel={firstParam(searchParams?.panel)}
        focusedDeploymentId={firstParam(searchParams?.deployment_id)}
        approvedChangePackage={
          changePackage &&
          (changePackage.status === "approved" ||
            changePackage.status === "deployable")
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

import { EditHistoryScrubber } from "@/components/agents/edit-history-scrubber";
import { AgentVersionsList } from "@/components/agents/agent-versions-list";
import { ReleaseCandidatePanel } from "@/components/agents/release-candidate-panel";
import { listAgentWorkflow } from "@/lib/agent-workflow";
import { listAgentVersions } from "@/lib/agent-versions";

export const dynamic = "force-dynamic";

interface AgentVersionsPageProps {
  params: { agent_id: string };
  searchParams?: { version_id?: string | string[] | undefined } | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * Versions tab — list every deploy for this agent and let reviewers
 * compare the ``config_json`` of any version to its predecessor. The
 * data path goes through the live ``GET /v1/agents/{id}/versions`` cp-api
 * route and shows a degraded state instead of demo deploy history when the
 * control plane is not configured.
 */
export default async function AgentVersionsPage({
  params,
  searchParams,
}: AgentVersionsPageProps) {
  const [versionPage, workflow] = await Promise.all([
    listAgentVersions(params.agent_id, {
      pageSize: 100,
    }),
    listAgentWorkflow(params.agent_id).catch((error: unknown) => ({
      branches: [],
      change_sets: [],
      release_candidates: [],
      degraded_reason:
        error instanceof Error
          ? error.message
          : "Could not load release workflow.",
    })),
  ]);
  return (
    <div className="flex flex-col gap-4" data-testid="agent-versions-tab">
      <h2 className="text-lg font-medium">Versions</h2>
      <ReleaseCandidatePanel
        agentId={params.agent_id}
        initialWorkflow={workflow}
      />
      <EditHistoryScrubber agentId={params.agent_id} />
      <AgentVersionsList
        versions={versionPage.items}
        focusedVersionId={firstParam(searchParams?.version_id)}
        degradedReason={versionPage.degraded_reason}
      />
    </div>
  );
}

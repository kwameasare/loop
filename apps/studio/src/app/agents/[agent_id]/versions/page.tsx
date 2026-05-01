import { AgentVersionsList } from "@/components/agents/agent-versions-list";
import { listAgentVersions } from "@/lib/agent-versions";

export const dynamic = "force-dynamic";

interface AgentVersionsPageProps {
  params: { agent_id: string };
}

/**
 * Versions tab — list every deploy for this agent and let reviewers
 * compare the ``config_json`` of any version to its predecessor. The
 * data path goes through ``listAgentVersions`` which today returns a
 * studio-local fixture; once cp-api ships ``GET /v1/agents/{id}/versions``
 * (follow-up S560) the fetch can be swapped in place.
 */
export default async function AgentVersionsPage({
  params,
}: AgentVersionsPageProps) {
  const { items } = await listAgentVersions(params.agent_id, {
    pageSize: 100,
  });
  return (
    <div className="flex flex-col gap-4" data-testid="agent-versions-tab">
      <h2 className="text-lg font-medium">Versions</h2>
      <AgentVersionsList versions={items} />
    </div>
  );
}

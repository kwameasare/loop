import { AgentVersionsTable } from "@/components/agents/agent-versions-table";
import { listAgentVersions } from "@/lib/cp-api";

export const dynamic = "force-dynamic";

interface AgentVersionsPageProps {
  params: { agent_id: string };
  searchParams?: { cursor?: string | string[] };
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AgentVersionsPage({
  params,
  searchParams,
}: AgentVersionsPageProps) {
  const page = await listAgentVersions(params.agent_id, {
    cursor: firstParam(searchParams?.cursor),
    limit: 10,
  });

  return (
    <AgentVersionsTable
      agentId={params.agent_id}
      versions={page.versions}
      nextCursor={page.next_cursor}
    />
  );
}

import { KbList } from "@/components/agents/kb-list";
import { listKbDocuments } from "@/lib/kb";

export const dynamic = "force-dynamic";

interface AgentKbPageProps {
  params: { agent_id: string };
}

export default async function AgentKbPage({ params }: AgentKbPageProps) {
  const { items } = await listKbDocuments(params.agent_id);
  return (
    <div data-testid="agent-kb">
      <KbList agentId={params.agent_id} initialDocuments={items} />
    </div>
  );
}

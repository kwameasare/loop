import { KnowledgeAtelier } from "@/components/knowledge/knowledge-atelier";
import { listKbDocuments } from "@/lib/kb";

export const dynamic = "force-dynamic";

interface AgentKbPageProps {
  params: { agent_id: string };
}

export default async function AgentKbPage({ params }: AgentKbPageProps) {
  const { items } = await listKbDocuments(params.agent_id);
  return (
    <div data-testid="agent-kb">
      <KnowledgeAtelier agentId={params.agent_id} initialDocuments={items} />
    </div>
  );
}

import { KnowledgeAtelier } from "@/components/knowledge/knowledge-atelier";
import { listKbDocuments } from "@/lib/kb";

export const dynamic = "force-dynamic";

interface AgentKbPageProps {
  params: { agent_id: string };
}

export default async function AgentKbPage({ params }: AgentKbPageProps) {
  const { items, degraded_reason } = await listKbDocuments(
    params.agent_id,
  ).catch((error: unknown) => ({
    items: [],
    degraded_reason:
      error instanceof Error
        ? `Knowledge service error: ${error.message}`
        : "Knowledge service error: Studio cannot verify source documents right now.",
  }));
  return (
    <div data-testid="agent-kb">
      <KnowledgeAtelier
        agentId={params.agent_id}
        degradedReason={degraded_reason}
        initialDocuments={items}
      />
    </div>
  );
}

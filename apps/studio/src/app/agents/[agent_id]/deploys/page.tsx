import { DeployTimeline } from "@/components/agents/deploy-timeline";
import { listDeployments } from "@/lib/deploys";

export const dynamic = "force-dynamic";

interface AgentDeploysPageProps {
  params: { agent_id: string };
}

export default async function AgentDeploysPage({ params }: AgentDeploysPageProps) {
  const { items } = await listDeployments(params.agent_id);
  return (
    <div data-testid="agent-deploys">
      <DeployTimeline agentId={params.agent_id} initialDeployments={items} />
    </div>
  );
}

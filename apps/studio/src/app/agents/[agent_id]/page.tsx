/**
 * S159: Agent overview tab -- description, model, last-deploy summary,
 * and edit-description modal.
 */
import { getAgent } from "@/lib/cp-api";
import { AgentOverview, type DeploySummary } from "@/components/agents/agent-overview";

interface AgentOverviewPageProps {
  params: { agent_id: string };
}

export default async function AgentOverviewPage({ params }: AgentOverviewPageProps) {
  const agent = await getAgent(params.agent_id);

  // Derive last-deploy summary from the agent summary until a dedicated
  // deploys endpoint is wired. active_version serves as a version proxy;
  // updated_at approximates deploy time.
  const lastDeploy: DeploySummary = {
    deployed_at: agent.active_version !== null ? agent.updated_at : null,
    version: agent.active_version,
    status: agent.active_version !== null ? "active" : null,
  };

  return (
    <AgentOverview
      id={agent.id}
      name={agent.name}
      description={agent.description}
      model=""
      lastDeploy={lastDeploy}
    />
  );
}

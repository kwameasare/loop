import { AgentHistoryWalkthrough } from "@/components/agents/agent-history-walkthrough";
import { fetchAgentHandoff, localAgentHandoff } from "@/lib/agent-handoff";

export const dynamic = "force-dynamic";

interface PageProps {
  params: { agent_id: string };
}

export default async function AgentHistoryPage({ params }: PageProps) {
  let model = localAgentHandoff(params.agent_id);
  try {
    model = await fetchAgentHandoff(params.agent_id);
  } catch {
    model = localAgentHandoff(params.agent_id);
  }

  return (
    <AgentHistoryWalkthrough agentId={params.agent_id} initialModel={model} />
  );
}

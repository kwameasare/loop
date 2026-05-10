import { AgentHistoryWalkthrough } from "@/components/agents/agent-history-walkthrough";
import {
  fetchAgentHandoff,
  type AgentHandoffModel,
} from "@/lib/agent-handoff";

export const dynamic = "force-dynamic";

interface PageProps {
  params: { agent_id: string };
}

export default async function AgentHistoryPage({ params }: PageProps) {
  let model: AgentHandoffModel;
  try {
    model = await fetchAgentHandoff(params.agent_id);
  } catch (error) {
    return (
      <p className="p-6 text-sm text-destructive" role="alert">
        {error instanceof Error
          ? error.message
          : "Could not load agent handoff history."}
      </p>
    );
  }

  return (
    <AgentHistoryWalkthrough agentId={params.agent_id} initialModel={model} />
  );
}

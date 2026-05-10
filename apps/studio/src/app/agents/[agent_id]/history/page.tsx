import { AgentHistoryWalkthrough } from "@/components/agents/agent-history-walkthrough";
import { SectionDegraded } from "@/components/section-states";
import { fetchAgentHandoff, type AgentHandoffModel } from "@/lib/agent-handoff";

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
      <main className="mx-auto max-w-3xl p-6">
        <SectionDegraded
          title="History Walkthrough"
          description="Agent handoff history could not load from the control plane."
          evidence={
            error instanceof Error
              ? error.message
              : "Could not load agent handoff history."
          }
        />
      </main>
    );
  }

  return (
    <AgentHistoryWalkthrough agentId={params.agent_id} initialModel={model} />
  );
}

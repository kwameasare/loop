import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentEvalsPage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="Evals"
      purpose="Eval coverage belongs inside the agent workbench so preview failures, reviewer comments, operator resolutions, and migration gaps become regression cases without leaving agent context."
      requiredObjects={[
        "Eval suites",
        "Eval cases",
        "Source trace links",
        "Expected behavior",
        "Risk tags",
        "Release gate result",
      ]}
      primaryHref={`/evals?agent_id=${encodeURIComponent(params.agent_id)}`}
      primaryLabel="Open Eval Foundry"
    />
  );
}

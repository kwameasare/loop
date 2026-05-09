import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentTracesPage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="Traces"
      purpose="Trace evidence should be adjacent to editing. A builder should inspect prompt context, retrieval, tool calls, memory writes, policy checks, cost, latency, and output from the same agent context."
      requiredObjects={[
        "Trace ID",
        "Version and branch",
        "Channel binding",
        "Span timeline",
        "Replay reference",
        "Eval conversion",
      ]}
      primaryHref={`/traces?agent_id=${encodeURIComponent(params.agent_id)}`}
      primaryLabel="Open Trace Theater"
    />
  );
}

import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentObservabilityPage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="Observability"
      purpose="Agent-level observability focuses on health, incidents, drift, cost, latency, escalations, channel failures, and production tail for the selected agent."
      requiredObjects={[
        "Health signals",
        "Incident links",
        "Drift clusters",
        "Cost and latency deltas",
        "Channel failures",
        "Owner notifications",
      ]}
      primaryHref={`/observe?agent_id=${encodeURIComponent(params.agent_id)}`}
      primaryLabel="Open Observatory"
    />
  );
}

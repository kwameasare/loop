import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentContractPage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="Contract"
      purpose="The Commitment Document defines responsibility, boundaries, owners, success metrics, worst-case failure, channels, and escalation policy for this agent."
      requiredObjects={[
        "Commitment Document",
        "Owner and backup owner",
        "Scope and out-of-scope behavior",
        "Success metrics",
        "Escalation policy",
        "Version history",
      ]}
      primaryHref={`/agents/${params.agent_id}`}
      primaryLabel="Return to overview work queue"
    />
  );
}

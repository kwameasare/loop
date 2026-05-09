import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentHistoryPage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="History"
      purpose="The history walkthrough supports handoff: a new owner should understand commitments, changes, approvals, deploys, rollbacks, incidents, comments, and open risks without oral tradition."
      requiredObjects={[
        "Commitment versions",
        "Change packages",
        "Approvals",
        "Deployments and rollbacks",
        "Incidents",
        "Open risks",
      ]}
      primaryHref={`/agents/${params.agent_id}/versions`}
      primaryLabel="Open versions"
    />
  );
}

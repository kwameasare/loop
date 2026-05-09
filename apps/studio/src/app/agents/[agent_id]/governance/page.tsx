import { AgentSectionPlaceholder } from "@/components/agents/agent-section-placeholder";

interface PageProps {
  params: { agent_id: string };
}

export default function AgentGovernancePage({ params }: PageProps) {
  return (
    <AgentSectionPlaceholder
      title="Governance"
      purpose="Governance makes approvals, policy requirements, audit records, secrets, residency, and evidence exports visible inside the agent workbench before any production-impacting change."
      requiredObjects={[
        "Approval policy",
        "Content hash",
        "Audit events",
        "Secret grants",
        "Residency posture",
        "Evidence export",
      ]}
      primaryHref={`/enterprise/govern?agent_id=${encodeURIComponent(
        params.agent_id,
      )}`}
      primaryLabel="Open governance center"
    />
  );
}

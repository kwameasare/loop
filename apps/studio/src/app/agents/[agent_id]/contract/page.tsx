import { AgentContractPanel } from "@/components/agents/agent-contract-panel";
import {
  buildLocalCommitmentDocument,
  fetchCurrentCommitment,
} from "@/lib/agent-commitment";

interface PageProps {
  params: { agent_id: string };
}

export default async function AgentContractPage({ params }: PageProps) {
  let commitment = buildLocalCommitmentDocument(params.agent_id);
  try {
    commitment = await fetchCurrentCommitment(params.agent_id);
  } catch {
    commitment = buildLocalCommitmentDocument(params.agent_id);
  }

  return (
    <AgentContractPanel
      agentId={params.agent_id}
      initialDocument={commitment}
    />
  );
}

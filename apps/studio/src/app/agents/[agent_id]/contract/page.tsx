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
  let degradedReason: string | undefined;
  try {
    commitment = await fetchCurrentCommitment(params.agent_id);
  } catch (error) {
    commitment = buildLocalCommitmentDocument(params.agent_id);
    degradedReason =
      error instanceof Error
        ? error.message
        : "Could not load the current Commitment Document.";
  }

  return (
    <AgentContractPanel
      agentId={params.agent_id}
      initialDocument={commitment}
      degradedReason={degradedReason}
    />
  );
}

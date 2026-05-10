import { AgentContractPanel } from "@/components/agents/agent-contract-panel";
import {
  buildLocalCommitmentDocument,
  fetchCurrentCommitment,
} from "@/lib/agent-commitment";

interface PageProps {
  params: { agent_id: string };
  searchParams?: { commitment_id?: string | string[] | undefined } | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AgentContractPage({
  params,
  searchParams,
}: PageProps) {
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
      focusedCommitmentId={firstParam(searchParams?.commitment_id)}
      degradedReason={degradedReason}
    />
  );
}

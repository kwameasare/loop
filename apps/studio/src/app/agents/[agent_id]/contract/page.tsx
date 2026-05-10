import { AgentContractPanel } from "@/components/agents/agent-contract-panel";
import {
  buildLocalCommitmentDocument,
  fetchCurrentCommitment,
  listCommitments,
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
  let history = [commitment];
  let degradedReason: string | undefined;
  let historyDegradedReason: string | undefined;
  try {
    commitment = await fetchCurrentCommitment(params.agent_id);
    history = [commitment];
  } catch (error) {
    commitment = buildLocalCommitmentDocument(params.agent_id);
    history = [commitment];
    degradedReason =
      error instanceof Error
        ? error.message
        : "Could not load the current Commitment Document.";
  }
  try {
    history = (await listCommitments(params.agent_id)).items;
  } catch (error) {
    historyDegradedReason =
      error instanceof Error
        ? error.message
        : "Could not load Commitment Document version history.";
  }

  return (
    <AgentContractPanel
      agentId={params.agent_id}
      initialDocument={commitment}
      initialHistory={history}
      focusedCommitmentId={firstParam(searchParams?.commitment_id)}
      degradedReason={degradedReason}
      historyDegradedReason={historyDegradedReason}
    />
  );
}

import { EmulatorPanel } from "@/components/agents/emulator-panel";
import { EvidenceCallout } from "@/components/target";

export const dynamic = "force-dynamic";

interface AgentSimulatorPageProps {
  params: { agent_id: string };
}

export default function AgentSimulatorPage({
  params,
}: AgentSimulatorPageProps): JSX.Element {
  return (
    <div className="grid gap-4" data-testid="agent-simulator">
      <EvidenceCallout
        title="Simulator Lab"
        tone="info"
        source="canonical UX section 15"
      >
        Re-render the same conversation across web, Slack, WhatsApp, SMS, and
        voice; use Inline ChatOps to swap models, disable tools, inject context,
        replay from a turn, or diff against another version.
      </EvidenceCallout>
      <EmulatorPanel agentId={params.agent_id} />
    </div>
  );
}

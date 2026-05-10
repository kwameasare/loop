import { EmulatorPanel } from "@/components/agents/emulator-panel";
import { EvidenceCallout } from "@/components/target";

export const dynamic = "force-dynamic";

interface AgentSimulatorPageProps {
  params: { agent_id: string };
  searchParams?: { view?: string | string[] | undefined } | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default function AgentSimulatorPage({
  params,
  searchParams,
}: AgentSimulatorPageProps): JSX.Element {
  const focusChannels = firstParam(searchParams?.view) === "channels";

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
      <EmulatorPanel
        agentId={params.agent_id}
        evidenceMode="empty"
        focusChannels={focusChannels}
      />
    </div>
  );
}

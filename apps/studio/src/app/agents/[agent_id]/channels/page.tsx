import { WebChannelCard } from "@/components/agents/web-channel-card";
import { getWebChannel } from "@/lib/web-channels";

export const dynamic = "force-dynamic";

interface AgentChannelsPageProps {
  params: { agent_id: string };
}

export default async function AgentChannelsPage({
  params,
}: AgentChannelsPageProps) {
  const binding = await getWebChannel(params.agent_id);
  return (
    <div className="flex flex-col gap-3" data-testid="agent-channels">
      <header>
        <h2 className="text-lg font-medium">Channels</h2>
        <p className="text-sm text-muted-foreground">
          Bind this agent to web, WhatsApp, voice, or Slack channels.
        </p>
      </header>
      <WebChannelCard
        agentId={params.agent_id}
        initialBinding={binding}
      />
    </div>
  );
}

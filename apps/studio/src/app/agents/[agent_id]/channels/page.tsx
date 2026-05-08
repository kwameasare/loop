import { WebChannelCard } from "@/components/agents/web-channel-card";
import { ChannelTypeGrid } from "@/components/channels/channel-type-grid";
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
          Bind this agent to web chat, WhatsApp, Telegram, Slack, Teams, SMS,
          email, and voice without splitting behavior across products.
        </p>
      </header>
      <ChannelTypeGrid agentId={params.agent_id} />
      <section className="rounded-md border bg-card p-4">
        <div className="mb-3">
          <h3 className="text-sm font-semibold">Web chat embed</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Enable the browser channel for this agent. Other channel packs keep
            the same agent, eval, memory, and deploy contract.
          </p>
        </div>
      <WebChannelCard
        agentId={params.agent_id}
        initialBinding={binding}
      />
      </section>
    </div>
  );
}

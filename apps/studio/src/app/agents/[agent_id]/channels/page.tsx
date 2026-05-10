import { WebChannelCard } from "@/components/agents/web-channel-card";
import { ChannelBindingsPanel } from "@/components/channels/channel-bindings-panel";
import { ChannelPreviewMatrix } from "@/components/channels/channel-preview-matrix";
import { ChannelTypeGrid } from "@/components/channels/channel-type-grid";
import {
  buildLocalChannelBindings,
  listChannelBindings,
} from "@/lib/channel-bindings";
import { type WebChannelBinding, getWebChannel } from "@/lib/web-channels";

export const dynamic = "force-dynamic";

interface AgentChannelsPageProps {
  params: { agent_id: string };
}

export default async function AgentChannelsPage({
  params,
}: AgentChannelsPageProps) {
  let bindings = buildLocalChannelBindings(params.agent_id);
  let bindingsDegradedReason: string | undefined;
  try {
    const result = await listChannelBindings(params.agent_id);
    bindings = result.items;
    bindingsDegradedReason = result.degraded_reason;
  } catch (err) {
    bindings = buildLocalChannelBindings(params.agent_id);
    bindingsDegradedReason =
      err instanceof Error
        ? err.message
        : "Channel binding status requires cp-api.";
  }

  let binding: WebChannelBinding = {
    agentId: params.agent_id,
    status: "disabled",
    channelId: null,
    token: null,
    enabledAt: null,
  };
  try {
    binding = await getWebChannel(params.agent_id);
  } catch {
    binding = {
      agentId: params.agent_id,
      status: "disabled",
      channelId: null,
      token: null,
      enabledAt: null,
    };
  }

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
      <ChannelBindingsPanel
        agentId={params.agent_id}
        initialBindings={bindings}
        degradedReason={bindingsDegradedReason}
      />
      <ChannelPreviewMatrix agentId={params.agent_id} bindings={bindings} />
      <section className="rounded-md border bg-card p-4">
        <div className="mb-3">
          <h3 className="text-sm font-semibold">Web chat embed</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Enable the browser channel for this agent. Other channel packs keep
            the same agent, eval, memory, and deploy contract.
          </p>
        </div>
        <WebChannelCard agentId={params.agent_id} initialBinding={binding} />
      </section>
    </div>
  );
}

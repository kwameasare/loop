import { WebChannelCard } from "@/components/agents/web-channel-card";
import { ChannelBindingsPanel } from "@/components/channels/channel-bindings-panel";
import { ChannelPreviewMatrix } from "@/components/channels/channel-preview-matrix";
import { ChannelTypeGrid } from "@/components/channels/channel-type-grid";
import {
  listChannelBindings,
  type ChannelBinding,
  type ChannelBindingType,
} from "@/lib/channel-bindings";
import { type WebChannelBinding, getWebChannel } from "@/lib/web-channels";

export const dynamic = "force-dynamic";

interface AgentChannelsPageProps {
  params: { agent_id: string };
  searchParams?:
    | {
        channel?: string | string[] | undefined;
        binding_id?: string | string[] | undefined;
        view?: string | string[] | undefined;
      }
    | undefined;
}

function firstParam(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function AgentChannelsPage({
  params,
  searchParams,
}: AgentChannelsPageProps) {
  let bindings: ChannelBinding[] = [];
  let bindingsDegradedReason: string | undefined;
  try {
    const result = await listChannelBindings(params.agent_id);
    bindings = result.items;
    bindingsDegradedReason = result.degraded_reason;
  } catch (err) {
    bindingsDegradedReason =
      err instanceof Error
        ? err.message
        : "Channel binding status requires cp-api.";
  }
  const focusedChannelType =
    parseFocusedChannel(searchParams?.channel) ??
    channelTypeForBindingId(bindings, searchParams?.binding_id);
  const focusReadiness = firstParam(searchParams?.view) === "readiness";

  let binding: WebChannelBinding = {
    agentId: params.agent_id,
    status: "disabled",
    channelId: null,
    token: null,
    enabledAt: null,
  };
  let webChannelDegradedReason: string | undefined;
  try {
    binding = await getWebChannel(params.agent_id);
  } catch (err) {
    webChannelDegradedReason =
      err instanceof Error
        ? err.message
        : "Web channel status requires cp-api.";
    binding = {
      agentId: params.agent_id,
      status: "disabled",
      channelId: null,
      token: null,
      enabledAt: null,
      degradedReason: webChannelDegradedReason,
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
        focusedChannelType={focusedChannelType}
        focusReadiness={focusReadiness}
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
        <WebChannelCard
          agentId={params.agent_id}
          degradedReason={webChannelDegradedReason}
          initialBinding={binding}
        />
      </section>
    </div>
  );
}

const CHANNEL_TYPES = new Set<ChannelBindingType>([
  "web_chat",
  "whatsapp",
  "telegram",
  "slack",
  "teams",
  "sms",
  "email",
  "voice",
  "webhook_api",
]);

function parseFocusedChannel(
  value: string | string[] | undefined,
): ChannelBindingType | undefined {
  const raw = Array.isArray(value) ? value[0] : value;
  if (!raw) return undefined;
  return CHANNEL_TYPES.has(raw as ChannelBindingType)
    ? (raw as ChannelBindingType)
    : undefined;
}

function channelTypeForBindingId(
  bindings: readonly { id: string; channel_type: ChannelBindingType }[],
  value: string | string[] | undefined,
): ChannelBindingType | undefined {
  const raw = Array.isArray(value) ? value[0] : value;
  if (!raw) return undefined;
  return bindings.find((binding) => binding.id === raw)?.channel_type;
}

import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";

export type ChannelBindingType =
  | "web_chat"
  | "whatsapp"
  | "telegram"
  | "slack"
  | "teams"
  | "sms"
  | "email"
  | "voice"
  | "webhook_api";

export type ChannelBindingStatus =
  | "not_configured"
  | "draft"
  | "ready"
  | "staged"
  | "live"
  | "paused"
  | "error"
  | "archived";

export type ChannelReadinessStatus =
  | "pending"
  | "passed"
  | "failed"
  | "not_required";

export interface ChannelReadinessCheck {
  id: string;
  label: string;
  status: ChannelReadinessStatus;
  evidence_ref: string | null;
  message: string;
}

export interface ChannelBinding {
  id: string;
  workspace_id: string;
  agent_id: string;
  channel_type: ChannelBindingType;
  provider: string;
  display_name: string;
  status: ChannelBindingStatus;
  identity_config: Record<string, unknown>;
  auth_config_ref: string | null;
  readiness: ChannelReadinessCheck[];
  last_traffic_at: string | null;
  last_failure_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelBindingListResponse {
  items: ChannelBinding[];
}

export interface ChannelBindingInput {
  channel_type: ChannelBindingType;
  provider?: string;
  display_name?: string;
  status?: ChannelBindingStatus;
  identity_config?: Record<string, unknown>;
  auth_config_ref?: string | null;
}

export const CHANNEL_ORDER: readonly ChannelBindingType[] = [
  "web_chat",
  "whatsapp",
  "telegram",
  "slack",
  "teams",
  "sms",
  "email",
  "voice",
  "webhook_api",
] as const;

export function channelLabel(channelType: ChannelBindingType): string {
  return {
    web_chat: "Web chat",
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    slack: "Slack",
    teams: "Teams",
    sms: "SMS",
    email: "Email",
    voice: "Voice",
    webhook_api: "Webhook/API",
  }[channelType];
}

function defaultProvider(channelType: ChannelBindingType): string {
  return {
    web_chat: "Loop Web",
    whatsapp: "Twilio or Meta Cloud API",
    telegram: "Telegram Bot API",
    slack: "Slack Platform",
    teams: "Microsoft Teams",
    sms: "Twilio SMS",
    email: "Loop Mail Router",
    voice: "LiveKit + Twilio",
    webhook_api: "Signed HTTPS",
  }[channelType];
}

function readiness(channelType: ChannelBindingType): ChannelReadinessCheck[] {
  const labels: Record<ChannelBindingType, string[]> = {
    web_chat: [
      "Domain verified",
      "Snippet minted",
      "Test conversation passed",
      "Trace capture enabled",
    ],
    whatsapp: [
      "Business identity verified",
      "Template approved",
      "Test inbound message passed",
      "Handoff route configured",
    ],
    telegram: [
      "Bot token verified",
      "Test command passed",
      "Trace capture enabled",
    ],
    slack: [
      "Workspace installed",
      "Test mention passed",
      "Thread reply passed",
      "Permissions approved",
    ],
    teams: [
      "Tenant installed",
      "Test mention passed",
      "Thread reply passed",
      "Permissions approved",
    ],
    sms: ["Number active", "Opt-out verified", "Test message passed"],
    email: ["Sender verified", "Inbound route tested", "Reply route tested"],
    voice: [
      "Number provisioned",
      "Test call passed",
      "ASR/TTS spans captured",
      "Transfer route tested",
    ],
    webhook_api: [
      "Endpoint verified",
      "Signature verification configured",
      "Retry policy tested",
    ],
  };
  return labels[channelType].map((label) => ({
    id: label
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_")
      .replace(/_$/, ""),
    label,
    status: "pending",
    evidence_ref: null,
    message: "",
  }));
}

export function buildLocalChannelBindings(agentId: string): ChannelBinding[] {
  const now = new Date().toISOString();
  return CHANNEL_ORDER.map((channelType) => ({
    id: `cb_local_${channelType}`,
    workspace_id: "",
    agent_id: agentId,
    channel_type: channelType,
    provider: defaultProvider(channelType),
    display_name: channelLabel(channelType),
    status: "not_configured",
    identity_config: {},
    auth_config_ref: null,
    readiness: readiness(channelType),
    last_traffic_at: null,
    last_failure_at: null,
    created_at: now,
    updated_at: now,
  }));
}

export async function listChannelBindings(
  agentId: string,
  opts: UxWireupClientOptions = {},
): Promise<ChannelBindingListResponse> {
  return cpJson<ChannelBindingListResponse>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings`,
    {
      ...opts,
      fallback: { items: buildLocalChannelBindings(agentId) },
    },
  );
}

export async function upsertChannelBinding(
  agentId: string,
  input: ChannelBindingInput,
  opts: UxWireupClientOptions = {},
): Promise<ChannelBinding> {
  return cpJson<ChannelBinding>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        ...buildLocalChannelBindings(agentId).find(
          (item) => item.channel_type === input.channel_type,
        )!,
        ...input,
        provider: input.provider ?? defaultProvider(input.channel_type),
        display_name: input.display_name ?? channelLabel(input.channel_type),
        status: input.status ?? "draft",
        updated_at: new Date().toISOString(),
      },
    },
  );
}

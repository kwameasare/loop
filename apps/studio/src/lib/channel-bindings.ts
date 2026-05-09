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

export interface ChannelPreviewFailure {
  id: string;
  severity: "blocker" | "warning";
  message: string;
  expected_outcome: string;
}

export interface ChannelPreviewEvalCaseSeed {
  scenario_title: string;
  channel_type: ChannelBindingType;
  binding_id: string;
  user_message: string;
  rendered_preview: string;
  expected_outcome: string;
  failure_reason: string;
  source_ref: string;
}

export interface ChannelPreviewRow {
  binding_id: string;
  channel_type: ChannelBindingType;
  display_name: string;
  provider: string;
  binding_status: ChannelBindingStatus;
  readiness_state: "not_configured" | "needs_readiness" | "blocked" | "ready";
  rendered_preview: string;
  adaptation_notes: string[];
  constraints: string[];
  formatting_failures: ChannelPreviewFailure[];
  eval_case_seed: ChannelPreviewEvalCaseSeed;
}

export interface ChannelPreviewMatrixRequest {
  scenario_title: string;
  user_message: string;
  expected_outcome: string;
  channel_types: ChannelBindingType[];
}

export interface ChannelPreviewMatrixResponse {
  agent_id: string;
  scenario_title: string;
  user_message: string;
  expected_outcome: string;
  rows: ChannelPreviewRow[];
  summary: {
    channels: number;
    formatting_failures: number;
    ready_channels: number;
  };
}

export interface ChannelPreviewEvalCaseResponse {
  ok: boolean;
  suite_id: string;
  case_id: string;
  case: Record<string, unknown>;
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

function previewText(
  channelType: ChannelBindingType,
  scenarioTitle: string,
  userMessage: string,
  expectedOutcome: string,
) {
  const compact =
    expectedOutcome.length > 140
      ? `${expectedOutcome.slice(0, 139).trim()}...`
      : expectedOutcome;
  if (channelType === "email") {
    return `Subject: ${scenarioTitle}\n\n${expectedOutcome}\n\nOriginal message: ${userMessage}`;
  }
  if (channelType === "voice") {
    return `Spoken answer: ${compact} Then ask one confirmation question.`;
  }
  if (channelType === "sms") {
    return expectedOutcome.length > 180
      ? `${expectedOutcome.slice(0, 179).trim()}...`
      : expectedOutcome;
  }
  if (channelType === "webhook_api") {
    return JSON.stringify(
      { scenario: scenarioTitle, message: userMessage, expected: compact },
      null,
      2,
    );
  }
  return `${compact}\n\nChannel controls preserve the same agent behavior.`;
}

function localReadinessState(
  binding: ChannelBinding,
): ChannelPreviewRow["readiness_state"] {
  if (binding.status === "not_configured") return "not_configured";
  const required = binding.readiness.filter(
    (check) => check.status !== "not_required",
  );
  if (required.some((check) => check.status === "failed")) return "blocked";
  if (required.every((check) => check.status === "passed")) return "ready";
  return "needs_readiness";
}

export function buildLocalPreviewMatrix(
  agentId: string,
  input: ChannelPreviewMatrixRequest,
  bindings = buildLocalChannelBindings(agentId),
): ChannelPreviewMatrixResponse {
  const selected = new Set(input.channel_types);
  const rows = bindings
    .filter(
      (binding) => selected.size === 0 || selected.has(binding.channel_type),
    )
    .map((binding) => {
      const rendered = previewText(
        binding.channel_type,
        input.scenario_title,
        input.user_message,
        input.expected_outcome,
      );
      const failures: ChannelPreviewFailure[] = [];
      if (binding.status === "not_configured") {
        failures.push({
          id: `${binding.channel_type}_not_configured`,
          severity: "blocker",
          message: `${binding.display_name} is not configured.`,
          expected_outcome: "Configure the channel binding before rollout.",
        });
      }
      if (binding.channel_type === "sms" && rendered.length > 160) {
        failures.push({
          id: "sms_too_long",
          severity: "warning",
          message: "SMS preview exceeds 160 characters.",
          expected_outcome: input.expected_outcome.slice(0, 140),
        });
      }
      return {
        binding_id: binding.id,
        channel_type: binding.channel_type,
        display_name: binding.display_name,
        provider: binding.provider,
        binding_status: binding.status,
        readiness_state: localReadinessState(binding),
        rendered_preview: rendered,
        adaptation_notes: [
          `Adapted for ${channelLabel(binding.channel_type)}.`,
        ],
        constraints: binding.readiness.slice(0, 3).map((check) => check.label),
        formatting_failures: failures,
        eval_case_seed: {
          scenario_title: input.scenario_title,
          channel_type: binding.channel_type,
          binding_id: binding.id,
          user_message: input.user_message,
          rendered_preview: rendered,
          expected_outcome: input.expected_outcome,
          failure_reason: failures[0]?.message ?? "",
          source_ref: `channel-preview/${binding.id}/${input.scenario_title}`,
        },
      } satisfies ChannelPreviewRow;
    });
  return {
    agent_id: agentId,
    scenario_title: input.scenario_title,
    user_message: input.user_message,
    expected_outcome: input.expected_outcome,
    rows,
    summary: {
      channels: rows.length,
      formatting_failures: rows.reduce(
        (count, row) => count + row.formatting_failures.length,
        0,
      ),
      ready_channels: rows.filter((row) => row.readiness_state === "ready")
        .length,
    },
  };
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

export async function previewChannelMatrix(
  agentId: string,
  input: ChannelPreviewMatrixRequest,
  opts: UxWireupClientOptions = {},
): Promise<ChannelPreviewMatrixResponse> {
  return cpJson<ChannelPreviewMatrixResponse>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/preview-matrix`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: buildLocalPreviewMatrix(agentId, input),
    },
  );
}

export async function createChannelPreviewEvalCase(
  agentId: string,
  input: ChannelPreviewEvalCaseSeed,
  opts: UxWireupClientOptions = {},
): Promise<ChannelPreviewEvalCaseResponse> {
  return cpJson<ChannelPreviewEvalCaseResponse>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/preview-matrix/eval-cases`,
    {
      ...opts,
      method: "POST",
      body: input,
      fallback: {
        ok: true,
        suite_id: "local_channel_formatting_failures",
        case_id: `local_${input.channel_type}_${input.binding_id}`,
        case: {
          source: "channel-preview-matrix",
          source_ref: input.source_ref,
        },
      },
    },
  );
}

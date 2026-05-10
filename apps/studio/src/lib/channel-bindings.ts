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

export type ChannelRequiredConfigStatus =
  | "configured"
  | "missing"
  | "pending_verification"
  | "blocked";

export interface ChannelRequiredConfigItem {
  id: string;
  label: string;
  status: ChannelRequiredConfigStatus;
  source: "identity_config" | "auth_config_ref" | "readiness" | "provider";
  key: string;
  evidence_ref: string | null;
  value_summary: string;
}

export interface ChannelReadinessSummary {
  state: "not_configured" | "needs_readiness" | "blocked" | "ready";
  passed: number;
  failed: number;
  pending: number;
  total: number;
  blocking_check_ids: string[];
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
  required_config: ChannelRequiredConfigItem[];
  readiness_summary: ChannelReadinessSummary;
  last_traffic_at: string | null;
  last_failure_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChannelBindingListResponse {
  items: ChannelBinding[];
  degraded_reason?: string | undefined;
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

export interface ChannelReadinessInput {
  status: ChannelReadinessStatus;
  evidence_ref?: string | null;
  message?: string;
}

export interface ChannelActivityInput {
  status: "success" | "failure";
  trace_id?: string;
  occurred_at?: string | null;
  failure_message?: string;
}

type ChannelBindingClientOptions = UxWireupClientOptions & {
  allowFixture?: boolean;
};

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

const READINESS_CHECKS: Record<
  ChannelBindingType,
  ReadonlyArray<Pick<ChannelReadinessCheck, "id" | "label">>
> = {
  web_chat: [
    { id: "domain_verified", label: "Domain verified" },
    { id: "snippet_minted", label: "Snippet minted" },
    { id: "test_conversation", label: "Test conversation passed" },
    { id: "trace_capture", label: "Trace capture enabled" },
  ],
  whatsapp: [
    { id: "business_verified", label: "Business identity verified" },
    { id: "template_approved", label: "Template approved" },
    { id: "test_inbound", label: "Test inbound message passed" },
    { id: "handoff_route", label: "Handoff route configured" },
  ],
  telegram: [
    { id: "token_verified", label: "Bot token verified" },
    { id: "test_command", label: "Test command passed" },
    { id: "trace_capture", label: "Trace capture enabled" },
  ],
  slack: [
    { id: "workspace_installed", label: "Workspace installed" },
    { id: "test_mention", label: "Test mention passed" },
    { id: "thread_reply", label: "Thread reply passed" },
    { id: "permissions_approved", label: "Permissions approved" },
  ],
  teams: [
    { id: "workspace_installed", label: "Workspace installed" },
    { id: "test_mention", label: "Test mention passed" },
    { id: "thread_reply", label: "Thread reply passed" },
    { id: "permissions_approved", label: "Permissions approved" },
  ],
  sms: [
    { id: "number_active", label: "Number active" },
    { id: "opt_out_verified", label: "Opt-out verified" },
    { id: "test_message", label: "Test message passed" },
  ],
  email: [
    { id: "sender_verified", label: "Sender verified" },
    { id: "inbound_tested", label: "Inbound route tested" },
    { id: "reply_tested", label: "Reply route tested" },
  ],
  voice: [
    { id: "number_provisioned", label: "Number provisioned" },
    { id: "test_call", label: "Test call passed" },
    { id: "asr_tts_spans", label: "ASR/TTS spans captured" },
    { id: "transfer_route", label: "Transfer route tested" },
  ],
  webhook_api: [
    { id: "signed_request", label: "Signed request verified" },
    { id: "retry_behavior", label: "Retry behavior tested" },
    { id: "trace_capture", label: "Trace capture enabled" },
  ],
};

function readiness(channelType: ChannelBindingType): ChannelReadinessCheck[] {
  return READINESS_CHECKS[channelType].map(({ id, label }) => ({
    id,
    label,
    status: "pending",
    evidence_ref: null,
    message: "",
  }));
}

function channelTypeForReadinessCheck(
  checkId: string,
): ChannelBindingType | null {
  for (const channelType of CHANNEL_ORDER) {
    if (READINESS_CHECKS[channelType].some((check) => check.id === checkId)) {
      return channelType;
    }
  }
  return null;
}

type RequiredConfigTemplate = {
  id: string;
  label: string;
  source: ChannelRequiredConfigItem["source"];
  key: string;
  keys?: string[];
};

const REQUIRED_CONFIG: Record<ChannelBindingType, RequiredConfigTemplate[]> = {
  web_chat: [
    {
      id: "embed_snippet",
      label: "Embed snippet",
      source: "readiness",
      key: "snippet_minted",
    },
    {
      id: "domain_allowlist",
      label: "Domain allowlist",
      source: "identity_config",
      key: "domain",
      keys: ["domain_allowlist", "domain"],
    },
    {
      id: "theme",
      label: "Theme",
      source: "identity_config",
      key: "theme",
      keys: ["theme", "theme_id"],
    },
    {
      id: "session_identity",
      label: "Session identity",
      source: "identity_config",
      key: "session_identity",
      keys: ["session_identity", "identity"],
    },
    {
      id: "handoff_route",
      label: "Handoff route",
      source: "identity_config",
      key: "handoff_route",
      keys: ["handoff_route", "handoff_queue"],
    },
    {
      id: "transcript_capture",
      label: "Transcript capture",
      source: "readiness",
      key: "trace_capture",
    },
  ],
  whatsapp: [
    {
      id: "business_account",
      label: "Business account",
      source: "identity_config",
      key: "business_account_id",
      keys: ["business_account_id", "business_account", "handle"],
    },
    {
      id: "provider_connection",
      label: "Provider connection",
      source: "auth_config_ref",
      key: "auth_config_ref",
    },
    {
      id: "template_approvals",
      label: "Template approvals",
      source: "readiness",
      key: "template_approved",
    },
    {
      id: "session_window_policy",
      label: "Session window policy",
      source: "identity_config",
      key: "session_window_policy",
    },
    {
      id: "media_policy",
      label: "Media policy",
      source: "identity_config",
      key: "media_policy",
    },
    {
      id: "opt_in_out_policy",
      label: "Opt-in/out policy",
      source: "identity_config",
      key: "opt_in_out_policy",
      keys: ["opt_in_out_policy", "opt_policy"],
    },
  ],
  telegram: [
    {
      id: "bot_token",
      label: "Bot token",
      source: "auth_config_ref",
      key: "auth_config_ref",
    },
    {
      id: "command_policy",
      label: "Command policy",
      source: "identity_config",
      key: "command_policy",
    },
    {
      id: "group_direct_policy",
      label: "Group/direct policy",
      source: "identity_config",
      key: "group_direct_policy",
    },
    {
      id: "attachment_policy",
      label: "Attachment policy",
      source: "identity_config",
      key: "attachment_policy",
    },
    {
      id: "abuse_controls",
      label: "Abuse controls",
      source: "identity_config",
      key: "abuse_controls",
    },
  ],
  slack: [
    {
      id: "workspace_installation",
      label: "Workspace installation",
      source: "readiness",
      key: "workspace_installed",
    },
    {
      id: "mention_policy",
      label: "Mention policy",
      source: "identity_config",
      key: "mention_policy",
    },
    {
      id: "thread_policy",
      label: "Thread policy",
      source: "identity_config",
      key: "thread_policy",
    },
    {
      id: "slash_commands",
      label: "Slash commands",
      source: "identity_config",
      key: "slash_commands",
    },
    {
      id: "internal_identity_mapping",
      label: "Internal identity mapping",
      source: "identity_config",
      key: "identity_mapping",
      keys: ["identity_mapping", "internal_identity_mapping"],
    },
    {
      id: "private_channel_policy",
      label: "Private channel policy",
      source: "identity_config",
      key: "private_channel_policy",
    },
  ],
  teams: [
    {
      id: "workspace_installation",
      label: "Workspace installation",
      source: "readiness",
      key: "workspace_installed",
    },
    {
      id: "mention_policy",
      label: "Mention policy",
      source: "identity_config",
      key: "mention_policy",
    },
    {
      id: "thread_policy",
      label: "Thread policy",
      source: "identity_config",
      key: "thread_policy",
    },
    {
      id: "slash_commands",
      label: "Slash commands",
      source: "identity_config",
      key: "slash_commands",
    },
    {
      id: "internal_identity_mapping",
      label: "Internal identity mapping",
      source: "identity_config",
      key: "identity_mapping",
      keys: ["identity_mapping", "internal_identity_mapping"],
    },
    {
      id: "private_channel_policy",
      label: "Private channel policy",
      source: "identity_config",
      key: "private_channel_policy",
    },
  ],
  sms: [
    {
      id: "number",
      label: "Number",
      source: "identity_config",
      key: "phone_number",
      keys: ["phone_number", "number"],
    },
    { id: "provider", label: "Provider", source: "provider", key: "provider" },
    {
      id: "opt_out_policy",
      label: "Opt-out policy",
      source: "readiness",
      key: "opt_out_verified",
    },
    {
      id: "carrier_compliance",
      label: "Carrier compliance",
      source: "identity_config",
      key: "carrier_compliance",
    },
    {
      id: "message_length_policy",
      label: "Message length policy",
      source: "identity_config",
      key: "message_length_policy",
    },
  ],
  email: [
    {
      id: "inbox",
      label: "Inbox",
      source: "identity_config",
      key: "inbox",
      keys: ["inbox", "inbound_address"],
    },
    {
      id: "sender_identity",
      label: "Sender identity",
      source: "readiness",
      key: "sender_verified",
    },
    {
      id: "routing_rules",
      label: "Routing rules",
      source: "identity_config",
      key: "routing_rules",
    },
    {
      id: "attachment_policy",
      label: "Attachment policy",
      source: "identity_config",
      key: "attachment_policy",
    },
    {
      id: "sla_policy",
      label: "SLA policy",
      source: "identity_config",
      key: "sla_policy",
      keys: ["sla_policy", "sla"],
    },
    {
      id: "signature_policy",
      label: "Signature policy",
      source: "identity_config",
      key: "signature_policy",
    },
  ],
  voice: [
    {
      id: "phone_number",
      label: "Phone number",
      source: "readiness",
      key: "number_provisioned",
    },
    {
      id: "asr_provider",
      label: "ASR provider",
      source: "identity_config",
      key: "asr_provider",
    },
    {
      id: "tts_provider",
      label: "TTS provider",
      source: "identity_config",
      key: "tts_provider",
    },
    {
      id: "barge_in_policy",
      label: "Barge-in policy",
      source: "identity_config",
      key: "barge_in_policy",
    },
    {
      id: "transfer_policy",
      label: "Transfer policy",
      source: "identity_config",
      key: "transfer_policy",
    },
    {
      id: "recording_policy",
      label: "Recording policy",
      source: "identity_config",
      key: "recording_policy",
    },
    {
      id: "latency_budget",
      label: "Latency budget",
      source: "identity_config",
      key: "latency_budget",
    },
  ],
  webhook_api: [
    {
      id: "endpoint",
      label: "Endpoint",
      source: "identity_config",
      key: "endpoint_url",
      keys: ["endpoint_url", "endpoint"],
    },
    {
      id: "auth",
      label: "Auth",
      source: "auth_config_ref",
      key: "auth_config_ref",
    },
    {
      id: "signature_verification",
      label: "Signature verification",
      source: "readiness",
      key: "signed_request",
    },
    {
      id: "retry_policy",
      label: "Retry policy",
      source: "readiness",
      key: "retry_behavior",
    },
    {
      id: "idempotency_key",
      label: "Idempotency key",
      source: "identity_config",
      key: "idempotency_key",
    },
    {
      id: "rate_limits",
      label: "Rate limits",
      source: "identity_config",
      key: "rate_limits",
      keys: ["rate_limits", "rate_limit"],
    },
  ],
};

function configuredIdentityValue(
  identityConfig: Record<string, unknown>,
  keys: readonly string[],
): string {
  for (const key of keys) {
    const value = identityConfig[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
    if (value && typeof value === "object") return "configured";
  }
  return "";
}

function readinessSummary(
  status: ChannelBindingStatus,
  checks: ChannelReadinessCheck[],
): ChannelReadinessSummary {
  const required = checks.filter((check) => check.status !== "not_required");
  const passed = required.filter((check) => check.status === "passed");
  const failed = required.filter((check) => check.status === "failed");
  const pending = required.filter((check) => check.status === "pending");
  return {
    state:
      status === "not_configured"
        ? "not_configured"
        : failed.length > 0
          ? "blocked"
          : required.length > 0 && passed.length === required.length
            ? "ready"
            : "needs_readiness",
    passed: passed.length,
    failed: failed.length,
    pending: pending.length,
    total: required.length,
    blocking_check_ids: required
      .filter(
        (check) => check.status === "failed" || check.status === "pending",
      )
      .map((check) => check.id),
  };
}

function requiredConfig(
  channelType: ChannelBindingType,
  identityConfig: Record<string, unknown>,
  authConfigRef: string | null,
  provider: string,
  checks: ChannelReadinessCheck[],
): ChannelRequiredConfigItem[] {
  const readinessById = new Map(checks.map((check) => [check.id, check]));
  return REQUIRED_CONFIG[channelType].map((item) => {
    let status: ChannelRequiredConfigStatus = "missing";
    let evidenceRef: string | null = null;
    let valueSummary = "";
    if (item.source === "provider") {
      status = provider ? "configured" : "missing";
      valueSummary = provider;
    } else if (item.source === "auth_config_ref") {
      status = authConfigRef ? "configured" : "missing";
      evidenceRef = authConfigRef;
      valueSummary = authConfigRef ? "Secret reference bound" : "";
    } else if (item.source === "identity_config") {
      valueSummary = configuredIdentityValue(
        identityConfig,
        item.keys ?? [item.key],
      );
      status = valueSummary ? "configured" : "missing";
    } else {
      const check = readinessById.get(item.key);
      evidenceRef = check?.evidence_ref ?? null;
      valueSummary = check?.message ?? "";
      status =
        check?.status === "passed"
          ? "configured"
          : check?.status === "failed"
            ? "blocked"
            : "pending_verification";
    }
    return {
      id: item.id,
      label: item.label,
      status,
      source: item.source,
      key: item.key,
      evidence_ref: evidenceRef,
      value_summary: valueSummary,
    };
  });
}

export function buildLocalChannelBindings(agentId: string): ChannelBinding[] {
  const now = new Date().toISOString();
  return CHANNEL_ORDER.map((channelType) => {
    const checks = readiness(channelType);
    const provider = defaultProvider(channelType);
    return {
      id: `cb_local_${channelType}`,
      workspace_id: "",
      agent_id: agentId,
      channel_type: channelType,
      provider,
      display_name: channelLabel(channelType),
      status: "not_configured",
      identity_config: {},
      auth_config_ref: null,
      readiness: checks,
      required_config: requiredConfig(channelType, {}, null, provider, checks),
      readiness_summary: readinessSummary("not_configured", checks),
      last_traffic_at: null,
      last_failure_at: null,
      created_at: now,
      updated_at: now,
    };
  });
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
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelBindingListResponse> {
  try {
    return await cpJson<ChannelBindingListResponse>(
      `/agents/${encodeURIComponent(agentId)}/channel-bindings`,
      {
        ...opts,
        allowFallback: opts.allowFixture === true,
        fallback: { items: buildLocalChannelBindings(agentId) },
      },
    );
  } catch (err) {
    if (opts.allowFixture === true) throw err;
    const reason =
      err instanceof Error
        ? err.message
        : "Channel binding reads require cp-api.";
    return {
      items: [],
      degraded_reason:
        reason.includes("LOOP_CP_API_BASE_URL") ||
        reason.includes("Failed to fetch")
          ? "Channel binding status requires cp-api. Studio is not showing local channel bindings as live agent state."
          : reason,
    };
  }
}

export async function upsertChannelBinding(
  agentId: string,
  input: ChannelBindingInput,
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelBinding> {
  const localBinding = buildLocalChannelBindings(agentId).find(
    (item) => item.channel_type === input.channel_type,
  )!;
  const nextProvider = input.provider ?? defaultProvider(input.channel_type);
  const nextStatus = input.status ?? "draft";
  const nextIdentityConfig =
    input.identity_config ?? localBinding.identity_config;
  const nextAuthConfigRef =
    input.auth_config_ref === undefined
      ? localBinding.auth_config_ref
      : input.auth_config_ref;
  return cpJson<ChannelBinding>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localBinding,
        ...input,
        provider: nextProvider,
        display_name: input.display_name ?? channelLabel(input.channel_type),
        status: nextStatus,
        identity_config: nextIdentityConfig,
        auth_config_ref: nextAuthConfigRef,
        required_config: requiredConfig(
          input.channel_type,
          nextIdentityConfig,
          nextAuthConfigRef,
          nextProvider,
          localBinding.readiness,
        ),
        readiness_summary: readinessSummary(nextStatus, localBinding.readiness),
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function updateChannelReadiness(
  agentId: string,
  bindingId: string,
  checkId: string,
  input: ChannelReadinessInput,
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelBinding> {
  const localBinding =
    buildLocalChannelBindings(agentId).find((item) => item.id === bindingId) ??
    buildLocalChannelBindings(agentId).find(
      (item) => item.channel_type === channelTypeForReadinessCheck(checkId),
    ) ??
    buildLocalChannelBindings(agentId)[0]!;
  const nextReadiness = [
    {
      id: checkId,
      label: checkId.replace(/_/g, " "),
      status: input.status,
      evidence_ref: input.evidence_ref ?? null,
      message: input.message ?? "",
    },
  ];
  return cpJson<ChannelBinding>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/${encodeURIComponent(bindingId)}/readiness/${encodeURIComponent(checkId)}`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localBinding,
        id: bindingId,
        readiness: nextReadiness,
        required_config: requiredConfig(
          localBinding.channel_type,
          localBinding.identity_config,
          localBinding.auth_config_ref,
          localBinding.provider,
          nextReadiness,
        ),
        readiness_summary: readinessSummary(localBinding.status, nextReadiness),
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function recordChannelActivity(
  agentId: string,
  bindingId: string,
  input: ChannelActivityInput,
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelBinding> {
  const localBinding =
    buildLocalChannelBindings(agentId).find((item) => item.id === bindingId) ??
    buildLocalChannelBindings(agentId)[0]!;
  const occurredAt = input.occurred_at ?? new Date().toISOString();
  return cpJson<ChannelBinding>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/${encodeURIComponent(bindingId)}/activity`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: {
        ...localBinding,
        id: bindingId,
        last_traffic_at: occurredAt,
        last_failure_at:
          input.status === "failure"
            ? occurredAt
            : localBinding.last_failure_at,
        updated_at: new Date().toISOString(),
      },
    },
  );
}

export async function previewChannelMatrix(
  agentId: string,
  input: ChannelPreviewMatrixRequest,
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelPreviewMatrixResponse> {
  return cpJson<ChannelPreviewMatrixResponse>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/preview-matrix`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
      fallback: buildLocalPreviewMatrix(agentId, input),
    },
  );
}

export async function createChannelPreviewEvalCase(
  agentId: string,
  input: ChannelPreviewEvalCaseSeed,
  opts: ChannelBindingClientOptions = {},
): Promise<ChannelPreviewEvalCaseResponse> {
  return cpJson<ChannelPreviewEvalCaseResponse>(
    `/agents/${encodeURIComponent(agentId)}/channel-bindings/preview-matrix/eval-cases`,
    {
      ...opts,
      method: "POST",
      body: input,
      allowFallback: opts.allowFixture === true,
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

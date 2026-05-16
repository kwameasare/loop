"use client";

import { useMemo, useState } from "react";
import {
  Globe2,
  Hash,
  Mail,
  MessageCircle,
  MessagesSquare,
  PhoneCall,
  Send,
  Webhook,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  CHANNEL_ORDER,
  type ChannelBinding,
  type ChannelBindingInput,
  type ChannelRequiredConfigItem,
  type ChannelBindingType,
  type ChannelReadinessCheck,
  type ChannelReadinessInput,
  channelLabel,
  upsertChannelBinding as defaultUpsertChannelBinding,
  updateChannelReadiness as defaultUpdateChannelReadiness,
} from "@/lib/channel-bindings";
import { cn } from "@/lib/utils";

interface ChannelBindingsPanelProps {
  agentId: string;
  initialBindings: ChannelBinding[];
  degradedReason?: string | undefined;
  focusedChannelType?: ChannelBindingType | undefined;
  focusReadiness?: boolean | undefined;
  upsertChannelBinding?: (
    agentId: string,
    input: ChannelBindingInput,
  ) => Promise<ChannelBinding>;
  updateChannelReadiness?: (
    agentId: string,
    bindingId: string,
    checkId: string,
    input: ChannelReadinessInput,
  ) => Promise<ChannelBinding>;
}

const ICONS: Record<ChannelBindingType, LucideIcon> = {
  web_chat: Globe2,
  whatsapp: MessageCircle,
  telegram: Send,
  slack: Hash,
  teams: Hash,
  sms: MessagesSquare,
  email: Mail,
  voice: PhoneCall,
  webhook_api: Webhook,
};

const STATUS_CLASS: Record<ChannelBinding["status"], string> = {
  not_configured: "border-border bg-muted text-muted-foreground",
  draft: "border-info/40 bg-info/10 text-info",
  ready: "border-success/40 bg-success/10 text-success",
  staged: "border-warning/40 bg-warning/10 text-warning",
  live: "border-success/40 bg-success/10 text-success",
  paused: "border-warning/40 bg-warning/10 text-warning",
  error: "border-destructive/40 bg-destructive/10 text-destructive",
  archived: "border-border bg-muted text-muted-foreground",
};

const CONFIG_STATUS_CLASS: Record<ChannelRequiredConfigItem["status"], string> =
  {
    configured: "bg-success text-success-foreground",
    missing: "bg-muted text-muted-foreground",
    pending_verification: "bg-warning text-warning-foreground",
    blocked: "bg-destructive text-destructive-foreground",
  };

const CHANNEL_PROFILE: Record<
  ChannelBindingType,
  {
    messageFormat: string;
    interactionStyle: string;
    supportedActions: string;
    constraints: string;
    businessHours: string;
    consent: string;
    rateLimit: string;
    attachments: string;
    fallback: string;
    policy: string;
    requiredConfig: string[];
  }
> = {
  web_chat: {
    messageFormat: "Rich web message with links and buttons",
    interactionStyle: "Synchronous chat",
    supportedActions: "Chat, link-out, escalation, file request",
    constraints: "Domain, session, and embed policy",
    businessHours: "Workspace support hours",
    consent: "Cookie and privacy notice",
    rateLimit: "Workspace web quota",
    attachments: "Images and documents when enabled",
    fallback: "Human handoff or email capture",
    policy: "Web answer policy",
    requiredConfig: [
      "Embed snippet",
      "Domain allowlist",
      "Theme",
      "Session identity",
      "Handoff route",
      "Transcript capture",
    ],
  },
  whatsapp: {
    messageFormat: "Template-safe text with numbered options",
    interactionStyle: "Mobile messaging",
    supportedActions: "Replies, templates, media, escalation",
    constraints: "Template approval and opt-in window",
    businessHours: "Regional support hours",
    consent: "Opt-in required",
    rateLimit: "Provider template and message caps",
    attachments: "Provider-approved media only",
    fallback: "SMS or human queue",
    policy: "WhatsApp formatting policy",
    requiredConfig: [
      "Business account",
      "Provider connection",
      "Template approvals",
      "Session window policy",
      "Media policy",
      "Opt-in/out policy",
    ],
  },
  telegram: {
    messageFormat: "Bot text with commands and quick replies",
    interactionStyle: "Command and chat",
    supportedActions: "Commands, replies, escalation",
    constraints: "Bot token and command routing",
    businessHours: "Workspace support hours",
    consent: "User starts bot conversation",
    rateLimit: "Telegram bot limits",
    attachments: "Images and documents when enabled",
    fallback: "Human queue link",
    policy: "Telegram bot policy",
    requiredConfig: [
      "Bot token",
      "Command policy",
      "Group/direct policy",
      "Attachment policy",
      "Abuse controls",
    ],
  },
  slack: {
    messageFormat: "Threaded internal answer with actions",
    interactionStyle: "Workspace collaboration",
    supportedActions: "Mentions, threads, buttons, handoff",
    constraints: "Workspace install and scopes",
    businessHours: "Team hours",
    consent: "Workspace app installation",
    rateLimit: "Slack API method limits",
    attachments: "Files per workspace policy",
    fallback: "Thread escalation",
    policy: "Internal collaboration policy",
    requiredConfig: [
      "Workspace installation",
      "Mention policy",
      "Thread policy",
      "Slash commands",
      "Internal identity mapping",
      "Private channel policy",
    ],
  },
  teams: {
    messageFormat: "Threaded Teams answer with action cards",
    interactionStyle: "Tenant collaboration",
    supportedActions: "Mentions, threads, cards, handoff",
    constraints: "Tenant app approval and scopes",
    businessHours: "Team hours",
    consent: "Tenant app installation",
    rateLimit: "Microsoft Graph and Teams limits",
    attachments: "Files per tenant policy",
    fallback: "Thread escalation",
    policy: "Internal collaboration policy",
    requiredConfig: [
      "Workspace installation",
      "Mention policy",
      "Thread policy",
      "Slash commands",
      "Internal identity mapping",
      "Private channel policy",
    ],
  },
  sms: {
    messageFormat: "Short plain text",
    interactionStyle: "Async mobile text",
    supportedActions: "Replies, links, escalation",
    constraints: "Length, opt-out, carrier compliance",
    businessHours: "Regional support hours",
    consent: "Opt-in and opt-out required",
    rateLimit: "Carrier and provider caps",
    attachments: "MMS only when enabled",
    fallback: "Voice callback or human queue",
    policy: "SMS brevity and compliance policy",
    requiredConfig: [
      "Number",
      "Provider",
      "Opt-out policy",
      "Carrier compliance",
      "Message length policy",
    ],
  },
  email: {
    messageFormat: "Structured email with summary and next steps",
    interactionStyle: "Async long-form support",
    supportedActions: "Reply, route, summarize, escalate",
    constraints: "Sender reputation and mailbox routing",
    businessHours: "Mailbox SLA",
    consent: "Existing email thread or inbound route",
    rateLimit: "Mailbox and provider limits",
    attachments: "Workspace attachment policy",
    fallback: "Ticket queue",
    policy: "Email support policy",
    requiredConfig: [
      "Inbox",
      "Sender identity",
      "Routing rules",
      "Attachment policy",
      "SLA policy",
      "Signature policy",
    ],
  },
  voice: {
    messageFormat: "Short spoken answer with confirmation prompts",
    interactionStyle: "Real-time speech",
    supportedActions: "Speak, listen, barge-in, transfer",
    constraints: "Phone number, ASR/TTS, recording rules",
    businessHours: "Phone support hours",
    consent: "Call consent and recording notice",
    rateLimit: "Concurrent call capacity",
    attachments: "Not applicable",
    fallback: "Transfer or callback",
    policy: "Voice brevity and safety policy",
    requiredConfig: [
      "Phone number",
      "ASR provider",
      "TTS provider",
      "Barge-in policy",
      "Transfer policy",
      "Recording policy",
      "Latency budget",
    ],
  },
  webhook_api: {
    messageFormat: "Signed JSON payload",
    interactionStyle: "Programmatic request/response",
    supportedActions: "POST, retry, status callback",
    constraints: "Signature, timeout, retry policy",
    businessHours: "Always on unless paused",
    consent: "API client authorization",
    rateLimit: "Workspace API quota",
    attachments: "URLs or structured payload references",
    fallback: "Retry queue and dead-letter log",
    policy: "Webhook API contract policy",
    requiredConfig: [
      "Endpoint",
      "Auth",
      "Signature verification",
      "Retry policy",
      "Idempotency key",
      "Rate limits",
    ],
  },
};

function readinessCount(binding: ChannelBinding) {
  return {
    passed: binding.readiness_summary?.passed ?? 0,
    total:
      binding.readiness_summary?.total ??
      binding.readiness.filter((check) => check.status !== "not_required")
        .length,
  };
}

function configText(
  config: Record<string, unknown>,
  keys: readonly string[],
): string | null {
  for (const key of keys) {
    const value = config[key];
    if (typeof value === "string" && value.trim()) return value;
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
  }
  return null;
}

function identityLabel(binding: ChannelBinding): string {
  return (
    configText(binding.identity_config, [
      "handle",
      "phone_number",
      "email",
      "domain",
      "bot_username",
      "workspace",
      "tenant",
      "endpoint_url",
      "from_address",
      "identity",
    ]) ?? "Identity not configured"
  );
}

function formatTimestamp(value: string | null): string {
  if (!value) return "No traffic yet";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toISOString().replace("T", " ").slice(0, 16);
}

function sortedBindings(bindings: ChannelBinding[]) {
  const byType = new Map(
    bindings.map((binding) => [binding.channel_type, binding]),
  );
  return CHANNEL_ORDER.map((channelType) => byType.get(channelType)).filter(
    Boolean,
  ) as ChannelBinding[];
}

function draftButtonLabel(
  binding: ChannelBinding,
  busyType: ChannelBindingType | null,
  degradedReason?: string | undefined,
) {
  if (degradedReason) return "Backend required";
  if (busyType === binding.channel_type) return "Saving...";
  return binding.status === "not_configured" ? "Start setup" : "Edit setup";
}

function ContractField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 truncate">{value}</dd>
    </div>
  );
}

function identityKeyFor(channelType: ChannelBindingType): string {
  return {
    web_chat: "domain",
    whatsapp: "business_account",
    telegram: "bot_username",
    slack: "workspace",
    teams: "tenant",
    sms: "phone_number",
    email: "from_address",
    voice: "phone_number",
    webhook_api: "endpoint_url",
  }[channelType];
}

function identityLabelFor(channelType: ChannelBindingType): string {
  return {
    web_chat: "Allowed domain",
    whatsapp: "Business account",
    telegram: "Bot username",
    slack: "Workspace",
    teams: "Tenant",
    sms: "Phone number",
    email: "Sender address",
    voice: "Phone number",
    webhook_api: "Endpoint URL",
  }[channelType];
}

function draftFromBinding(binding: ChannelBinding) {
  const identityKey = identityKeyFor(binding.channel_type);
  return {
    provider: binding.provider,
    identity: configText(binding.identity_config, [identityKey]) ?? "",
    authConfigRef: binding.auth_config_ref ?? "",
  };
}

function readinessButtonLabel(
  check: ChannelReadinessCheck,
  status: ChannelReadinessInput["status"],
) {
  if (status === "passed") {
    return check.status === "passed" ? "Passed" : "Pass";
  }
  return check.status === "failed" ? "Failed" : "Fail";
}

function requiredConfigFor(
  binding: ChannelBinding,
  profile: (typeof CHANNEL_PROFILE)[ChannelBindingType],
): ChannelRequiredConfigItem[] {
  if (binding.required_config?.length) return binding.required_config;
  return profile.requiredConfig.map((label) => ({
    id: label.toLowerCase().replace(/[^a-z0-9]+/g, "_"),
    label,
    status: "missing",
    source: "identity_config",
    key: "",
    evidence_ref: null,
    value_summary: "",
  }));
}

export function ChannelBindingsPanel({
  agentId,
  initialBindings,
  degradedReason,
  focusedChannelType,
  focusReadiness = false,
  upsertChannelBinding = defaultUpsertChannelBinding,
  updateChannelReadiness = defaultUpdateChannelReadiness,
}: ChannelBindingsPanelProps) {
  const [bindings, setBindings] = useState(() =>
    sortedBindings(initialBindings),
  );
  const [busyType, setBusyType] = useState<ChannelBindingType | null>(null);
  const [editingType, setEditingType] = useState<ChannelBindingType | null>(
    focusedChannelType ?? null,
  );
  const [readinessBusy, setReadinessBusy] = useState<string | null>(null);
  const [setupDrafts, setSetupDrafts] = useState<
    Partial<
      Record<
        ChannelBindingType,
        { provider: string; identity: string; authConfigRef: string }
      >
    >
  >({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const ordered = useMemo(() => sortedBindings(bindings), [bindings]);

  function openSetup(binding: ChannelBinding) {
    setEditingType(binding.channel_type);
    setSetupDrafts((previous) => ({
      ...previous,
      [binding.channel_type]:
        previous[binding.channel_type] ?? draftFromBinding(binding),
    }));
    setNotice(null);
  }

  async function handleDraft(channelType: ChannelBindingType) {
    const current = ordered.find(
      (binding) => binding.channel_type === channelType,
    );
    if (!current) return;
    const draft = setupDrafts[channelType] ?? draftFromBinding(current);
    const identityKey = identityKeyFor(channelType);
    setBusyType(channelType);
    setError(null);
    setNotice(null);
    try {
      const input: ChannelBindingInput = {
        channel_type: channelType,
        display_name: current.display_name ?? channelLabel(channelType),
        status: "draft",
        identity_config: {
          ...current.identity_config,
          [identityKey]: draft.identity,
        },
        auth_config_ref: draft.authConfigRef || null,
      };
      if (draft.provider) input.provider = draft.provider;
      const updated = await upsertChannelBinding(agentId, input);
      setBindings((previous) =>
        sortedBindings([
          ...previous.filter((item) => item.channel_type !== channelType),
          updated,
        ]),
      );
      setEditingType(updated.channel_type);
      setNotice(`${updated.display_name} setup draft saved.`);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Channel binding setup requires cp-api.",
      );
    } finally {
      setBusyType(null);
    }
  }

  async function markReadiness(
    binding: ChannelBinding,
    check: ChannelReadinessCheck,
    status: ChannelReadinessInput["status"],
  ) {
    const busyKey = `${binding.id}:${check.id}:${status}`;
    setReadinessBusy(busyKey);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateChannelReadiness(
        agentId,
        binding.id,
        check.id,
        {
          status,
          evidence_ref: `manual/${binding.channel_type}/${check.id}`,
          message:
            status === "passed"
              ? `${check.label} verified from Studio channel readiness.`
              : `${check.label} failed during Studio channel readiness review.`,
        },
      );
      setBindings((previous) =>
        sortedBindings([
          ...previous.filter(
            (item) => item.channel_type !== updated.channel_type,
          ),
          updated,
        ]),
      );
      setNotice(
        `${updated.display_name} readiness ${check.label.toLowerCase()} marked ${status}.`,
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not update channel readiness.",
      );
    } finally {
      setReadinessBusy(null);
    }
  }

  return (
    <section
      className={cn(
        "space-y-4 instrument-panel rounded-2xl p-4",
        focusReadiness
          ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
          : "",
      )}
      data-testid="channel-bindings-panel"
      aria-labelledby="channel-bindings-heading"
    >
      <header className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 id="channel-bindings-heading" className="text-sm font-semibold">
            Channel bindings
          </h3>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            One governed agent can serve many channels. Voice is a channel
            binding, not a separate category or separate agent.
          </p>
        </div>
        <p className="rounded-md border bg-background px-3 py-2 text-xs text-muted-foreground">
          {ordered.length} peer bindings · readiness blocks only the affected
          channel
        </p>
      </header>

      {error ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      {notice ? (
        <p
          className="rounded-md border border-success/40 bg-success/10 p-3 text-sm text-success"
          role="status"
          data-testid="channel-bindings-notice"
        >
          {notice}
        </p>
      ) : null}

      {degradedReason ? (
        <div
          className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
          data-testid="channel-bindings-degraded"
          role="status"
        >
          <p className="font-medium">Live channel state is unavailable.</p>
          <p className="mt-1 text-xs">{degradedReason}</p>
        </div>
      ) : null}

      {focusReadiness ? (
        <div
          className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-info"
          data-testid="channel-readiness-focused-workbench-panel"
          role="status"
        >
          <p className="font-medium">Channel readiness</p>
          <p className="mt-1 text-xs">
            Opened from Workbench evidence. Confirm each peer channel has
            identity, auth, consent, rate-limit, fallback, eval coverage, and
            deployment readiness before promotion.
          </p>
        </div>
      ) : null}

      {ordered.length === 0 ? (
        <div
          className="rounded-md border bg-background p-4 text-sm"
          data-testid="channel-bindings-empty"
        >
          <p className="font-medium">
            {degradedReason
              ? "No live channel bindings loaded."
              : "No channel bindings configured yet."}
          </p>
          <p className="mt-1 max-w-2xl text-muted-foreground">
            {focusedChannelType
              ? `${channelLabel(focusedChannelType)} is selected in the channel catalog, but there is no authorized backend binding loaded for this agent.`
              : "Choose a channel above to start a backend-backed setup flow. Studio will not substitute local setup templates for current agent state."}
          </p>
        </div>
      ) : null}

      <div className="grid gap-3 xl:grid-cols-3">
        {ordered.map((binding) => {
          const Icon = ICONS[binding.channel_type];
          const readiness = readinessCount(binding);
          const profile = CHANNEL_PROFILE[binding.channel_type];
          const isFocused = binding.channel_type === focusedChannelType;
          const isEditing = editingType === binding.channel_type;
          const draft =
            setupDrafts[binding.channel_type] ?? draftFromBinding(binding);
          const identityKey = identityKeyFor(binding.channel_type);
          return (
            <article
              key={binding.channel_type}
              className={cn(
                "rounded-md border bg-background p-3",
                isFocused
                  ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
                  : "",
              )}
              data-testid={`channel-binding-${binding.channel_type}`}
              data-focused={isFocused ? "true" : "false"}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border bg-card">
                    <Icon className="h-4 w-4 text-primary" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <h4 className="truncate text-sm font-semibold">
                      {binding.display_name}
                    </h4>
                    <p className="mt-1 truncate text-xs text-muted-foreground">
                      {binding.provider}
                    </p>
                  </div>
                </div>
                <span
                  className={cn(
                    "shrink-0 rounded-md border px-2 py-0.5 text-[0.7rem] font-medium",
                    STATUS_CLASS[binding.status],
                  )}
                >
                  {binding.status.replace("_", " ")}
                </span>
              </div>

              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <dt className="font-medium uppercase tracking-wide text-muted-foreground">
                    Readiness
                  </dt>
                  <dd className="mt-1">
                    {readiness.passed}/{readiness.total} passed
                  </dd>
                </div>
                <div>
                  <dt className="font-medium uppercase tracking-wide text-muted-foreground">
                    Auth
                  </dt>
                  <dd className="mt-1 truncate">
                    {binding.auth_config_ref ? "bound" : "not bound"}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium uppercase tracking-wide text-muted-foreground">
                    Last traffic
                  </dt>
                  <dd className="mt-1 truncate">
                    {formatTimestamp(binding.last_traffic_at)}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium uppercase tracking-wide text-muted-foreground">
                    Last failure
                  </dt>
                  <dd className="mt-1 truncate">
                    {binding.last_failure_at
                      ? formatTimestamp(binding.last_failure_at)
                      : "No recent failure"}
                  </dd>
                </div>
              </dl>

              <dl
                className="mt-3 grid gap-2 rounded-md border bg-card/70 p-2 text-xs md:grid-cols-2"
                data-testid={`channel-binding-contract-${binding.channel_type}`}
              >
                <ContractField
                  label="Identity"
                  value={identityLabel(binding)}
                />
                <ContractField
                  label="Message format"
                  value={profile.messageFormat}
                />
                <ContractField
                  label="Interaction"
                  value={profile.interactionStyle}
                />
                <ContractField
                  label="Actions"
                  value={profile.supportedActions}
                />
                <ContractField
                  label="Constraints"
                  value={profile.constraints}
                />
                <ContractField
                  label="Business hours"
                  value={
                    configText(binding.identity_config, [
                      "business_hours",
                      "hours",
                      "sla",
                    ]) ?? profile.businessHours
                  }
                />
                <ContractField label="Consent" value={profile.consent} />
                <ContractField label="Rate limit" value={profile.rateLimit} />
                <ContractField
                  label="Attachments"
                  value={profile.attachments}
                />
                <ContractField label="Fallback" value={profile.fallback} />
                <ContractField label="Policy" value={profile.policy} />
                <ContractField
                  label="Eval coverage"
                  value={`${readiness.passed}/${readiness.total} channel checks`}
                />
                <ContractField
                  label="Deployment"
                  value={binding.status.replace("_", " ")}
                />
              </dl>

              <div
                className="mt-3 rounded-md border bg-card/70 p-2"
                data-testid={`channel-required-config-${binding.channel_type}`}
              >
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Required configuration
                </p>
                <ul className="mt-2 grid gap-1 text-xs text-muted-foreground">
                  {requiredConfigFor(binding, profile).map((item) => (
                    <li
                      key={item.id}
                      className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2"
                    >
                      <span
                        className={cn(
                          "h-1.5 w-1.5 rounded-full",
                          item.status === "configured"
                            ? "bg-success"
                            : item.status === "blocked"
                              ? "bg-destructive"
                              : item.status === "pending_verification"
                                ? "bg-warning"
                                : "bg-muted-foreground",
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[0.65rem] font-medium",
                          CONFIG_STATUS_CLASS[item.status],
                        )}
                      >
                        {item.status.replace("_", " ")}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <ul className="mt-3 space-y-1">
                {binding.readiness.slice(0, 4).map((check) => (
                  <li
                    key={check.id}
                    className="grid gap-2 rounded-md border bg-card/50 p-2 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-muted-foreground">
                        {check.label}
                      </span>
                      <span>{check.status.replace("_", " ")}</span>
                    </div>
                    {check.evidence_ref ? (
                      <span className="truncate text-muted-foreground">
                        Evidence: {check.evidence_ref}
                      </span>
                    ) : null}
                    <div className="grid grid-cols-2 gap-1">
                      {(["passed", "failed"] as const).map((status) => {
                        const busyKey = `${binding.id}:${check.id}:${status}`;
                        return (
                          <button
                            key={status}
                            type="button"
                            className="rounded-md border bg-background px-2 py-1 font-medium hover:bg-muted disabled:opacity-50"
                            disabled={
                              Boolean(degradedReason) ||
                              readinessBusy === busyKey ||
                              check.status === status
                            }
                            onClick={() =>
                              void markReadiness(binding, check, status)
                            }
                            data-testid={`channel-readiness-${status}-${binding.channel_type}-${check.id}`}
                          >
                            {readinessBusy === busyKey
                              ? "Saving"
                              : readinessButtonLabel(check, status)}
                          </button>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ul>

              {isEditing ? (
                <div
                  className="mt-3 grid gap-2 rounded-md border bg-card/80 p-3 text-xs"
                  data-testid={`channel-setup-${binding.channel_type}`}
                >
                  <p className="font-medium">Setup draft</p>
                  <label className="grid gap-1">
                    <span className="text-muted-foreground">Provider</span>
                    <input
                      className="rounded-md border bg-background px-2 py-1"
                      value={draft.provider}
                      onChange={(event) =>
                        setSetupDrafts((previous) => ({
                          ...previous,
                          [binding.channel_type]: {
                            ...draft,
                            provider: event.target.value,
                          },
                        }))
                      }
                      data-testid={`channel-provider-${binding.channel_type}`}
                    />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-muted-foreground">
                      {identityLabelFor(binding.channel_type)}
                    </span>
                    <input
                      className="rounded-md border bg-background px-2 py-1"
                      value={draft.identity}
                      onChange={(event) =>
                        setSetupDrafts((previous) => ({
                          ...previous,
                          [binding.channel_type]: {
                            ...draft,
                            identity: event.target.value,
                          },
                        }))
                      }
                      data-testid={`channel-identity-${binding.channel_type}`}
                    />
                    <span className="text-muted-foreground">
                      Stored as identity_config.{identityKey}.
                    </span>
                  </label>
                  <label className="grid gap-1">
                    <span className="text-muted-foreground">
                      Auth config ref
                    </span>
                    <input
                      className="rounded-md border bg-background px-2 py-1"
                      value={draft.authConfigRef}
                      onChange={(event) =>
                        setSetupDrafts((previous) => ({
                          ...previous,
                          [binding.channel_type]: {
                            ...draft,
                            authConfigRef: event.target.value,
                          },
                        }))
                      }
                      data-testid={`channel-auth-ref-${binding.channel_type}`}
                    />
                  </label>
                  <button
                    type="button"
                    className="rounded-md border bg-background px-3 py-2 font-medium hover:bg-muted disabled:opacity-50"
                    disabled={
                      busyType === binding.channel_type ||
                      Boolean(degradedReason)
                    }
                    onClick={() => void handleDraft(binding.channel_type)}
                    data-testid={`channel-setup-save-${binding.channel_type}`}
                  >
                    {busyType === binding.channel_type
                      ? "Saving setup"
                      : "Save setup draft"}
                  </button>
                </div>
              ) : null}

              <button
                type="button"
                className="mt-3 w-full rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-50"
                disabled={
                  busyType === binding.channel_type || Boolean(degradedReason)
                }
                onClick={() => {
                  openSetup(binding);
                  if (binding.status !== "not_configured") return;
                  void handleDraft(binding.channel_type);
                }}
                data-testid={`channel-binding-draft-${binding.channel_type}`}
              >
                {draftButtonLabel(binding, busyType, degradedReason)}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}

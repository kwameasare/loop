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
  type ChannelBindingType,
  channelLabel,
  upsertChannelBinding as defaultUpsertChannelBinding,
} from "@/lib/channel-bindings";
import { cn } from "@/lib/utils";

interface ChannelBindingsPanelProps {
  agentId: string;
  initialBindings: ChannelBinding[];
  degradedReason?: string | undefined;
  upsertChannelBinding?: (
    agentId: string,
    input: ChannelBindingInput,
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

function readinessCount(binding: ChannelBinding) {
  const required = binding.readiness.filter(
    (check) => check.status !== "not_required",
  );
  const passed = required.filter((check) => check.status === "passed");
  return { passed: passed.length, total: required.length };
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
  return binding.status === "not_configured" ? "Start setup" : "Update draft";
}

export function ChannelBindingsPanel({
  agentId,
  initialBindings,
  degradedReason,
  upsertChannelBinding = defaultUpsertChannelBinding,
}: ChannelBindingsPanelProps) {
  const [bindings, setBindings] = useState(() =>
    sortedBindings(initialBindings),
  );
  const [busyType, setBusyType] = useState<ChannelBindingType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ordered = useMemo(() => sortedBindings(bindings), [bindings]);

  async function handleDraft(channelType: ChannelBindingType) {
    const current = ordered.find(
      (binding) => binding.channel_type === channelType,
    );
    setBusyType(channelType);
    setError(null);
    try {
      const input: ChannelBindingInput = {
        channel_type: channelType,
        display_name: current?.display_name ?? channelLabel(channelType),
        status: "draft",
        identity_config: current?.identity_config ?? {},
        auth_config_ref: current?.auth_config_ref ?? null,
      };
      if (current?.provider) input.provider = current.provider;
      const updated = await upsertChannelBinding(agentId, input);
      setBindings((previous) =>
        sortedBindings([
          ...previous.filter((item) => item.channel_type !== channelType),
          updated,
        ]),
      );
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

  return (
    <section
      className="space-y-4 rounded-md border bg-card p-4"
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

      <div className="grid gap-3 xl:grid-cols-3">
        {ordered.map((binding) => {
          const Icon = ICONS[binding.channel_type];
          const readiness = readinessCount(binding);
          return (
            <article
              key={binding.channel_type}
              className="rounded-md border bg-background p-3"
              data-testid={`channel-binding-${binding.channel_type}`}
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
              </dl>

              <ul className="mt-3 space-y-1">
                {binding.readiness.slice(0, 4).map((check) => (
                  <li
                    key={check.id}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <span className="truncate text-muted-foreground">
                      {check.label}
                    </span>
                    <span>{check.status.replace("_", " ")}</span>
                  </li>
                ))}
              </ul>

              <button
                type="button"
                className="mt-3 w-full rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted disabled:opacity-50"
                disabled={
                  busyType === binding.channel_type || Boolean(degradedReason)
                }
                onClick={() => void handleDraft(binding.channel_type)}
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

import Link from "next/link";
import {
  Globe2,
  Hash,
  Mail,
  MessageCircle,
  MessagesSquare,
  PhoneCall,
  Send,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { ChannelBindingType } from "@/lib/channel-bindings";
import { cn } from "@/lib/utils";

interface ChannelType {
  id: string;
  label: string;
  setup: string;
  summary: string;
  focusType: ChannelBindingType;
  href: string;
  icon: LucideIcon;
}

function agentHref(
  agentId: string | null,
  fallback: string,
  channelType: ChannelBindingType,
): string {
  const query = `channel=${encodeURIComponent(channelType)}`;
  return agentId
    ? `/agents/${encodeURIComponent(agentId)}/channels?${query}`
    : `${fallback}?intent=channel&${query}`;
}

function channelTypes(agentId: string | null): readonly ChannelType[] {
  return [
    {
      id: "web",
      label: "Web chat",
      setup: "On your site",
      summary: "Drop the agent into your product or website.",
      focusType: "web_chat",
      href: agentHref(agentId, "/agents", "web_chat"),
      icon: Globe2,
    },
    {
      id: "whatsapp",
      label: "WhatsApp",
      setup: "Messaging",
      summary: "Reach customers on WhatsApp with templates and rich media.",
      focusType: "whatsapp",
      href: agentHref(agentId, "/agents", "whatsapp"),
      icon: MessageCircle,
    },
    {
      id: "telegram",
      label: "Telegram",
      setup: "Messaging",
      summary: "Replies, commands, and threads for Telegram audiences.",
      focusType: "telegram",
      href: agentHref(agentId, "/agents", "telegram"),
      icon: Send,
    },
    {
      id: "slack",
      label: "Slack",
      setup: "Internal",
      summary: "Where your team already works — threads, mentions, approvals.",
      focusType: "slack",
      href: agentHref(agentId, "/agents", "slack"),
      icon: Hash,
    },
    {
      id: "teams",
      label: "Teams",
      setup: "Internal",
      summary: "Microsoft Teams with single sign-on and channel-safe mentions.",
      focusType: "teams",
      href: agentHref(agentId, "/agents", "teams"),
      icon: Hash,
    },
    {
      id: "sms",
      label: "SMS",
      setup: "Messaging",
      summary: "Short, reliable replies with opt-out compliance.",
      focusType: "sms",
      href: agentHref(agentId, "/agents", "sms"),
      icon: MessagesSquare,
    },
    {
      id: "email",
      label: "Email",
      setup: "Async",
      summary: "Long-form replies with attachments and routing.",
      focusType: "email",
      href: agentHref(agentId, "/agents", "email"),
      icon: Mail,
    },
    {
      id: "voice",
      label: "Voice",
      setup: "Telephony",
      summary: "Phone calls with natural turn-taking and live escalation.",
      focusType: "voice",
      href: agentHref(agentId, "/agents", "voice"),
      icon: PhoneCall,
    },
    {
      id: "webhook_api",
      label: "Webhook / API",
      setup: "Programmatic",
      summary: "Wire the agent into your own product over a signed endpoint.",
      focusType: "webhook_api",
      href: agentHref(agentId, "/agents", "webhook_api"),
      icon: Globe2,
    },
  ];
}

export function ChannelTypeGrid({
  agentId = null,
  className,
}: {
  agentId?: string | null;
  className?: string;
}) {
  const channels = channelTypes(agentId);
  return (
    <div
      className={cn("grid gap-3 md:grid-cols-2 xl:grid-cols-3", className)}
      data-testid="channel-type-grid"
    >
      {channels.map((channel) => {
        const Icon = channel.icon;
        return (
          <Link
            key={channel.id}
            href={channel.href}
            data-testid={`channel-type-${channel.id}`}
            className="interactive-lift instrument-panel rounded-2xl p-4 transition-colors hover:bg-accent/55"
          >
            <div className="flex items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md border bg-background">
                <Icon className="h-4 w-4 text-primary" aria-hidden />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-semibold">
                  {channel.label}
                </span>
                <span className="mt-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {channel.setup}
                </span>
                <span className="mt-2 block text-sm text-muted-foreground">
                  {channel.summary}
                </span>
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

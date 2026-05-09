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

import { cn } from "@/lib/utils";

interface ChannelType {
  id: string;
  label: string;
  setup: string;
  summary: string;
  href: string;
  icon: LucideIcon;
}

function agentHref(agentId: string | null, fallback: string): string {
  return agentId ? `/agents/${encodeURIComponent(agentId)}/channels` : fallback;
}

function channelTypes(agentId: string | null): readonly ChannelType[] {
  const channelsHref = agentHref(agentId, "/agents");
  return [
    {
      id: "web",
      label: "Web chat",
      setup: "Agent binding",
      summary: "Embed the agent in an app or website with a scoped snippet.",
      href: channelsHref,
      icon: Globe2,
    },
    {
      id: "whatsapp",
      label: "WhatsApp",
      setup: "Agent binding",
      summary: "Template windows, handoff, media, and session policy.",
      href: channelsHref,
      icon: MessageCircle,
    },
    {
      id: "telegram",
      label: "Telegram",
      setup: "Agent binding",
      summary: "Bot token intake, command routing, and threaded traces.",
      href: channelsHref,
      icon: Send,
    },
    {
      id: "slack",
      label: "Slack",
      setup: "Agent binding",
      summary: "Threaded replies, slash commands, approvals, and mentions.",
      href: channelsHref,
      icon: Hash,
    },
    {
      id: "teams",
      label: "Teams",
      setup: "Agent binding",
      summary: "Tenant install, internal identity mapping, and safe mentions.",
      href: channelsHref,
      icon: Hash,
    },
    {
      id: "sms",
      label: "SMS",
      setup: "Agent binding",
      summary: "Concise responses, opt-out policy, and carrier-safe delivery.",
      href: channelsHref,
      icon: MessagesSquare,
    },
    {
      id: "email",
      label: "Email",
      setup: "Agent binding",
      summary: "Long-form replies, attachments, routing, and SLA handling.",
      href: channelsHref,
      icon: Mail,
    },
    {
      id: "voice",
      label: "Voice",
      setup: "Agent binding",
      summary: "Phone numbers, ASR/TTS, barge-in, and voice evals.",
      href: channelsHref,
      icon: PhoneCall,
    },
    {
      id: "webhook_api",
      label: "Webhook/API",
      setup: "Agent binding",
      summary: "Signed endpoint, retry policy, and event-shaped traces.",
      href: channelsHref,
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
            className="interactive-lift rounded-md border bg-card p-4 transition-colors hover:bg-accent/55"
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

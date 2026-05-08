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
  return [
    {
      id: "web",
      label: "Web chat",
      setup: "Agent binding",
      summary: "Embed the agent in an app or website with a scoped snippet.",
      href: agentHref(agentId, "/agents"),
      icon: Globe2,
    },
    {
      id: "whatsapp",
      label: "WhatsApp",
      setup: "Business channel pack",
      summary: "Template windows, handoff, media, and session policy.",
      href: "/marketplace",
      icon: MessageCircle,
    },
    {
      id: "telegram",
      label: "Telegram",
      setup: "Bot channel pack",
      summary: "Bot token intake, command routing, and threaded traces.",
      href: "/marketplace",
      icon: Send,
    },
    {
      id: "slack",
      label: "Slack / Teams",
      setup: "Workspace channel pack",
      summary: "Threaded replies, slash commands, approvals, and mentions.",
      href: "/marketplace",
      icon: Hash,
    },
    {
      id: "sms",
      label: "SMS",
      setup: "Messaging channel pack",
      summary: "Concise responses, opt-out policy, and carrier-safe delivery.",
      href: "/marketplace",
      icon: MessagesSquare,
    },
    {
      id: "email",
      label: "Email",
      setup: "Async channel pack",
      summary: "Long-form replies, attachments, routing, and SLA handling.",
      href: "/marketplace",
      icon: Mail,
    },
    {
      id: "voice",
      label: "Voice",
      setup: "Voice stage",
      summary: "Phone numbers, ASR/TTS, barge-in, and voice evals.",
      href: "/voice",
      icon: PhoneCall,
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

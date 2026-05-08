import Link from "next/link";
import { ArrowRight, Bot, Radio } from "lucide-react";

import { ChannelTypeGrid } from "@/components/channels/channel-type-grid";
import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { buttonVariants } from "@/components/ui/button";
import { listAgents } from "@/lib/cp-api";

export const dynamic = "force-dynamic";

export default async function ChannelsPage() {
  const { agents } = await listAgents().catch(() => ({ agents: [] }));
  const existingSlugs = agents.map((agent) => agent.slug).filter(Boolean);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 lg:p-6">
      <header className="rounded-md border bg-card p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Build
        </p>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Workspace channels
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Bind agents to the channels customers actually use: web chat,
              WhatsApp, Telegram, Slack, Teams, SMS, email, and voice.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/agents" className={buttonVariants()}>
              <Bot className="h-4 w-4" />
              Pick an agent
            </Link>
            <Link
              href="/voice"
              className={buttonVariants({ variant: "outline" })}
            >
              <Radio className="h-4 w-4" />
              Voice stage
            </Link>
          </div>
        </div>
      </header>

      <section className="rounded-md border bg-card p-5">
        <div className="mb-4">
          <h2 className="text-lg font-semibold">Channel types</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Voice is one channel type. The same agent contract should survive
            every text, chat, and telephony surface.
          </p>
        </div>
        <ChannelTypeGrid />
      </section>

      <section className="rounded-md border bg-card p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Agent bindings</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Configure channels from the agent workbench so behavior, tools,
              memory, evals, and deploy gates stay together.
            </p>
          </div>
          <NewAgentModal existingSlugs={existingSlugs} />
        </div>

        {agents.length > 0 ? (
          <div className="mt-4 divide-y rounded-md border">
            {agents.slice(0, 8).map((agent) => (
              <Link
                key={agent.id}
                href={`/agents/${encodeURIComponent(agent.id)}/channels`}
                className="flex items-center justify-between gap-4 p-3 text-sm transition-colors hover:bg-accent/55"
              >
                <span className="min-w-0">
                  <span className="block truncate font-medium">
                    {agent.name || "Untitled agent"}
                  </span>
                  <span className="block truncate text-muted-foreground">
                    {agent.description || agent.slug || "No description yet"}
                  </span>
                </span>
                <span className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground">
                  Configure
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No agents yet. Create or import an agent, then bind it to web chat,
            WhatsApp, Telegram, Slack, SMS, email, or voice.
          </div>
        )}
      </section>
    </main>
  );
}

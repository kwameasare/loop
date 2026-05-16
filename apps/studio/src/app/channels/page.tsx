import Link from "next/link";
import { ArrowRight, Bot, Radio } from "lucide-react";

import { ChannelTypeGrid } from "@/components/channels/channel-type-grid";
import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { buttonVariants } from "@/components/ui/button";
import { listAgents, type AgentSummary } from "@/lib/cp-api";
import { listWorkspaces, type Workspace } from "@/lib/workspaces";

export const dynamic = "force-dynamic";

export function resolveChannelsWorkspaceId(
  agents: AgentSummary[],
  workspaces: Workspace[],
  fallback: string | undefined = process.env.LOOP_DEFAULT_WORKSPACE_ID,
): string | null {
  return agents[0]?.workspace_id || workspaces[0]?.id || fallback || null;
}

export default async function ChannelsPage() {
  const { workspaces, degraded_reason: workspacesDegradedReason } =
    await listWorkspaces().catch((error: unknown) => ({
      workspaces: [],
      degraded_reason:
        error instanceof Error
          ? error.message
          : "Could not load workspace context.",
    }));
  const initialWorkspaceId = resolveChannelsWorkspaceId([], workspaces);
  const agentsResult = initialWorkspaceId
    ? await listAgents({ workspaceId: initialWorkspaceId })
        .then((result) => ({ ...result, degradedReason: undefined }))
        .catch((error: unknown) => ({
          agents: [],
          degradedReason:
            error instanceof Error ? error.message : "Could not load agents.",
        }))
    : {
        agents: [],
        degradedReason: "Workspace context is required before listing agents.",
      };
  const { agents, degradedReason: agentsDegradedReason } = agentsResult;
  const existingSlugs = agents.map((agent) => agent.slug).filter(Boolean);
  const activeAgentId = agents[0]?.id ?? null;
  const workspaceId = resolveChannelsWorkspaceId(
    agents,
    workspaces,
    initialWorkspaceId ?? undefined,
  );

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 lg:p-6">
      <header className="instrument-panel rounded-2xl p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Build
        </p>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Channels
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Connect your agents to the places customers and teams already
              spend their day — web, WhatsApp, Slack, voice, and the rest.
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
              Open voice channel stage
            </Link>
          </div>
        </div>
      </header>

      <section className="instrument-panel rounded-2xl p-5">
        <div className="mb-4">
          <h2 className="text-lg font-semibold">Channel types</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Nine ways your agents can talk to customers and teammates. The
            same agent shows up everywhere you bind it.
          </p>
        </div>
        <ChannelTypeGrid agentId={activeAgentId} />
      </section>

      <section className="instrument-panel rounded-2xl p-5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold">Your agents</h2>
            <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
              Pick an agent to connect channels. Behavior, tools, and
              guardrails all live in one place.
            </p>
          </div>
          <NewAgentModal
            existingSlugs={existingSlugs}
            workspaceId={workspaceId}
          />
        </div>

        {/* A workspace failure already implies the agents call will
            fail — show one consolidated notice instead of stacking two
            bordered warnings. Both test hooks remain so existing
            assertions still resolve. */}
        {workspacesDegradedReason ? (
          <div
            className="notice notice--warning mt-4"
            data-testid="channels-workspace-degraded"
            role="status"
          >
            <div className="notice__body">{workspacesDegradedReason}</div>
            {agentsDegradedReason ? (
              <span
                className="sr-only"
                data-testid="channels-agents-degraded"
              >
                {agentsDegradedReason}
              </span>
            ) : null}
          </div>
        ) : agentsDegradedReason ? (
          <div
            className="notice notice--warning mt-4"
            data-testid="channels-agents-degraded"
            role="status"
          >
            <div className="notice__body">
              Agent registry is unavailable. {agentsDegradedReason}
            </div>
          </div>
        ) : null}

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
        ) : agentsDegradedReason ? null : (
          <div className="mt-4 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No agents yet. Create or import one to start connecting channels.
          </div>
        )}
      </section>
    </main>
  );
}

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CircleAlert,
  GitBranch,
  Inbox,
  Radar,
  Rocket,
  TestTube2,
} from "lucide-react";

import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { MetricCountUp, StatePanel } from "@/components/target";
import { buttonVariants } from "@/components/ui/button";
import { listAgents, type AgentSummary } from "@/lib/cp-api";
import { cn } from "@/lib/utils";

export const dynamic = "force-dynamic";

interface QueueItem {
  id: string;
  title: string;
  detail: string;
  href: string;
  label: string;
  tone: "blocked" | "watch" | "ready";
}

function relativeDate(value: string): string {
  if (!value) return "No timestamp";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No timestamp";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function buildQueue(agents: AgentSummary[]): QueueItem[] {
  const drafts = agents.filter((agent) => agent.active_version === null);
  const production = agents.filter((agent) => agent.active_version !== null);
  const recent = [...agents]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 2);

  const queue: QueueItem[] = drafts.slice(0, 3).map((agent) => ({
    id: `draft-${agent.id}`,
    title: `${agent.name} has not reached production`,
    detail:
      agent.description ||
      "Finish behavior, tools, eval coverage, and deploy preflight.",
    href: `/agents/${agent.id}`,
    label: "Open workbench",
    tone: "blocked",
  }));

  if (production[0]) {
    queue.push({
      id: `trace-${production[0].id}`,
      title: `Review recent traces for ${production[0].name}`,
      detail: `Production v${production[0].active_version} is live; inspect spans before the next draft.`,
      href: "/traces",
      label: "Open traces",
      tone: "watch",
    });
  }

  for (const agent of recent) {
    if (queue.some((item) => item.id.endsWith(agent.id))) continue;
    queue.push({
      id: `recent-${agent.id}`,
      title: `${agent.name} was updated ${relativeDate(agent.updated_at)}`,
      detail: "Check whether this edit needs eval coverage or an approval.",
      href: `/agents/${agent.id}/versions`,
      label: "View versions",
      tone: "ready",
    });
  }

  return queue.slice(0, 5);
}

function QueueIcon({ tone }: { tone: QueueItem["tone"] }) {
  if (tone === "blocked") {
    return <CircleAlert className="h-4 w-4 text-warning" aria-hidden />;
  }
  if (tone === "watch")
    return <Radar className="h-4 w-4 text-info" aria-hidden />;
  return <GitBranch className="h-4 w-4 text-success" aria-hidden />;
}

export default async function HomePage() {
  const { agents } = await listAgents().catch(() => ({ agents: [] }));
  const existingSlugs = agents.map((agent) => agent.slug).filter(Boolean);
  const draftCount = agents.filter(
    (agent) => agent.active_version === null,
  ).length;
  const productionCount = agents.length - draftCount;
  const queue = buildQueue(agents);
  const primaryAgent = queue.find((item) => item.href.startsWith("/agents/"));

  if (agents.length === 0) {
    return (
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-4 lg:p-6">
        <section className="rounded-md border bg-card p-6">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Workspace queue
          </p>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight">
            Create or import your first agent
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Studio is empty until there is a real agent to inspect. Start from a
            blank workbench or import an existing Botpress-style bot.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <NewAgentModal existingSlugs={existingSlugs} />
            <Link
              href="/migrate"
              className={buttonVariants({ variant: "outline" })}
            >
              Import an agent
            </Link>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 lg:p-6">
      <header className="rounded-md border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Workspace queue
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              Agent operations
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              The next useful work across this workspace, based only on agents
              that exist here.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {primaryAgent ? (
              <Link
                href={primaryAgent.href}
                className={buttonVariants({ className: "gap-2" })}
              >
                Open top item
                <ArrowRight className="h-4 w-4" />
              </Link>
            ) : null}
            <NewAgentModal existingSlugs={existingSlugs} />
          </div>
        </div>
      </header>

      <section
        className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"
        aria-label="Workspace agent metrics"
      >
        <MetricCountUp
          label="Agents"
          value={agents.length}
          delta="Real workspace records"
        />
        <MetricCountUp
          label="Draft agents"
          value={draftCount}
          delta="Need evals and deploy preflight"
        />
        <MetricCountUp
          label="Production versions"
          value={productionCount}
          delta="Have an active version"
        />
        <MetricCountUp
          label="Inbox"
          value={0}
          delta="Open HITL queue for live handoffs"
        />
      </section>

      <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="rounded-md border bg-card">
          <div className="border-b px-4 py-3">
            <h2 className="text-base font-semibold">Needs attention</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              One list, one decision at a time. No simulated traces or demo
              conversations appear here.
            </p>
          </div>
          {queue.length > 0 ? (
            <ol className="divide-y">
              {queue.map((item) => (
                <li key={item.id} className="p-4">
                  <Link
                    href={item.href}
                    className="group flex items-start gap-3 rounded-md p-1 -m-1 transition-colors hover:bg-muted/60"
                  >
                    <span
                      className={cn(
                        "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md border",
                        item.tone === "blocked"
                          ? "bg-warning/10"
                          : item.tone === "watch"
                            ? "bg-info/10"
                            : "bg-success/10",
                      )}
                    >
                      <QueueIcon tone={item.tone} />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold">
                        {item.title}
                      </span>
                      <span className="mt-1 block text-sm text-muted-foreground">
                        {item.detail}
                      </span>
                    </span>
                    <span className="hidden shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground group-hover:text-foreground sm:inline-flex">
                      {item.label}
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <div className="p-4">
              <StatePanel state="success" title="No agent work is blocked">
                <p>
                  Open an agent workbench when you are ready to change behavior,
                  tools, memory, evals, or deploy state.
                </p>
              </StatePanel>
            </div>
          )}
        </div>

        <aside className="grid content-start gap-3">
          <Link
            href="/agents"
            className="rounded-md border bg-card p-4 transition-colors hover:bg-muted/50"
          >
            <Bot className="h-4 w-4 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-semibold">Agent registry</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Browse every workbench in this workspace.
            </p>
          </Link>
          <Link
            href="/evals"
            className="rounded-md border bg-card p-4 transition-colors hover:bg-muted/50"
          >
            <TestTube2 className="h-4 w-4 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-semibold">Eval Foundry</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Turn production failures into coverage.
            </p>
          </Link>
          <Link
            href="/deploys"
            className="rounded-md border bg-card p-4 transition-colors hover:bg-muted/50"
          >
            <Rocket className="h-4 w-4 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-semibold">Deploys</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Review canaries, approvals, and rollback posture.
            </p>
          </Link>
          <Link
            href="/inbox"
            className="rounded-md border bg-card p-4 transition-colors hover:bg-muted/50"
          >
            <Inbox className="h-4 w-4 text-primary" aria-hidden />
            <p className="mt-3 text-sm font-semibold">HITL Inbox</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Resolve human handoffs and save fixes as evals.
            </p>
          </Link>
        </aside>
      </section>
    </main>
  );
}

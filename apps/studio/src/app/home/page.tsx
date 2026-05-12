import Link from "next/link";
import {
  Bot,
  ChartNoAxesColumn,
  Clock3,
  ExternalLink,
  GitPullRequestArrow,
  Inbox,
  PackageOpen,
  Pin,
  TestTube2,
} from "lucide-react";

import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { EstateOverview } from "@/components/estate/estate-overview";
import { buttonVariants } from "@/components/ui/button";
import { listAgents, type AgentSummary } from "@/lib/cp-api";
import { fetchEstateHealth } from "@/lib/estate-health";
import { fetchHomepagePins, type HomepagePin } from "@/lib/homepage-pins";
import { listWorkspaces, type Workspace } from "@/lib/workspaces";

export const dynamic = "force-dynamic";

function QuickLink({
  href,
  title,
  detail,
  icon: Icon,
}: {
  href: string;
  title: string;
  detail: string;
  icon: typeof Bot;
}) {
  return (
    <Link
      href={href}
      className="rounded-md border bg-card p-4 transition-colors hover:bg-muted/50"
    >
      <Icon className="h-4 w-4 text-primary" aria-hidden />
      <p className="mt-3 text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </Link>
  );
}

function pinSourceLabel(sourceType: string): string {
  return sourceType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function PinnedWork({
  pins,
  degradedReason,
}: {
  pins: readonly HomepagePin[];
  degradedReason?: string | undefined;
}) {
  if (pins.length === 0 && !degradedReason) {
    return null;
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="homepage-pins"
      aria-label="Pinned work"
    >
      <div className="flex items-start gap-2">
        <Pin className="mt-0.5 h-4 w-4 text-primary" aria-hidden />
        <div>
          <p className="text-sm font-semibold">Pinned work</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Your saved traces, dashboards, evals, and investigation shortcuts.
          </p>
        </div>
      </div>
      {degradedReason ? (
        <p
          className="mt-3 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
          role="status"
        >
          {degradedReason}
        </p>
      ) : null}
      {pins.length ? (
        <ol className="mt-3 divide-y rounded-md border">
          {pins.slice(0, 5).map((pin) => (
            <li key={pin.id}>
              <Link
                href={pin.href}
                className="group flex items-start gap-3 p-3 transition-colors hover:bg-muted/50"
              >
                <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
                  <ChartNoAxesColumn className="h-3.5 w-3.5" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {pin.title}
                  </span>
                  <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span>{pinSourceLabel(pin.source_type)}</span>
                    <span aria-hidden>·</span>
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3 w-3" aria-hidden />
                      {new Date(pin.created_at).toLocaleDateString("en", {
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </span>
                </span>
                <ExternalLink
                  className="mt-1 h-3.5 w-3.5 text-muted-foreground transition-colors group-hover:text-foreground"
                  aria-hidden
                />
              </Link>
            </li>
          ))}
        </ol>
      ) : null}
    </section>
  );
}

export function resolveHomeWorkspaceId(
  agents: readonly AgentSummary[],
  workspaces: readonly Workspace[],
  fallback: string | undefined = process.env.LOOP_DEFAULT_WORKSPACE_ID,
): string | null {
  return agents[0]?.workspace_id || workspaces[0]?.id || fallback || null;
}

export function homeContextWarnings(
  agentsDegradedReason?: string | undefined,
  workspacesDegradedReason?: string | undefined,
): string[] {
  return [
    agentsDegradedReason
      ? `Agent registry unavailable: ${agentsDegradedReason}`
      : null,
    workspacesDegradedReason
      ? `Workspace context unavailable: ${workspacesDegradedReason}`
      : null,
  ].filter((item): item is string => Boolean(item));
}

export default async function HomePage() {
  const { workspaces, degraded_reason: workspacesDegradedReason } =
    await listWorkspaces().catch((error: unknown) => ({
      workspaces: [],
      degraded_reason:
        error instanceof Error
          ? error.message
          : "Could not load workspace context.",
    }));
  const initialWorkspaceId = resolveHomeWorkspaceId([], workspaces);
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
  const workspaceId = resolveHomeWorkspaceId(
    agents,
    workspaces,
    initialWorkspaceId ?? undefined,
  );
  const contextWarnings = homeContextWarnings(
    agentsDegradedReason,
    workspacesDegradedReason,
  );
  const estateHealth = await fetchEstateHealth(workspaceId, {
    fallbackAgents: agents,
  });
  const homepagePins = await fetchHomepagePins(workspaceId);

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-5 p-4 lg:grid-cols-[minmax(0,1fr)_20rem] lg:p-6">
      <div className="min-w-0">
        <EstateOverview health={estateHealth} />
      </div>

      <aside className="grid content-start gap-3" aria-label="Primary actions">
        <div className="rounded-md border bg-card p-4">
          <p className="text-sm font-semibold">Create or import</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Start from a governed contract, not a blank demo.
          </p>
          {contextWarnings.length > 0 ? (
            <div
              className="mt-3 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
              data-testid="home-context-degraded"
              role="status"
            >
              {contextWarnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex flex-col gap-2">
            <NewAgentModal
              existingSlugs={existingSlugs}
              workspaceId={workspaceId}
            />
            <Link href="/migrate" className={buttonVariants({ variant: "outline" })}>
              <PackageOpen className="mr-2 h-4 w-4" aria-hidden />
              Import agent
            </Link>
          </div>
        </div>

        <PinnedWork
          pins={homepagePins.items}
          degradedReason={homepagePins.degradedReason}
        />

        <QuickLink
          href="/agents"
          title="Agent registry"
          detail="Open the inventory and select a workbench."
          icon={Bot}
        />
        <QuickLink
          href="/evals"
          title="Eval Foundry"
          detail="Turn traces and reviews into deploy gates."
          icon={TestTube2}
        />
        <QuickLink
          href="/deploys"
          title="Deploys"
          detail="Review release candidates, approvals, and rollback."
          icon={GitPullRequestArrow}
        />
        <QuickLink
          href="/inbox"
          title="HITL Inbox"
          detail="Resolve human handoffs and preserve the lesson."
          icon={Inbox}
        />
      </aside>
    </main>
  );
}

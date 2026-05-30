import Link from "next/link";
import {
  ArrowUpRight,
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
import type { LucideIcon } from "lucide-react";

import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { EstateOverview } from "@/components/estate/estate-overview";
import { buttonVariants } from "@/components/ui/button";
import { listAgents, type AgentSummary } from "@/lib/cp-api";
import { fetchEstateHealth } from "@/lib/estate-health";
import { fetchHomepagePins, type HomepagePin } from "@/lib/homepage-pins";
import { getCpAccessToken } from "@/lib/server/session";
import { listWorkspaces, type Workspace } from "@/lib/workspaces";

export const dynamic = "force-dynamic";

function pinSourceLabel(sourceType: string): string {
  return sourceType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function RouteLink({
  href,
  title,
  detail,
  icon: Icon,
}: {
  href: string;
  title: string;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <Link
      href={href}
      className="interactive-lift group flex items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 text-sm hover:border-glass-border/60 hover:bg-card/60"
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-3.5 w-3.5" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium leading-tight">
          {title}
        </span>
        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
          {detail}
        </span>
      </span>
      <ArrowUpRight
        className="h-3.5 w-3.5 text-muted-foreground transition-transform duration-swift group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
        aria-hidden
      />
    </Link>
  );
}

function PinnedWork({
  pins,
  degradedReason,
}: {
  pins: readonly HomepagePin[];
  degradedReason?: string | undefined;
}) {
  // Hide the section entirely when the back-end is unavailable. The
  // single "cp-api unavailable" chip in the estate header is the
  // canonical signal — repeating it as a third boxed warning just
  // dominates the layout.
  if (pins.length === 0) {
    return null;
  }

  return (
    <section
      className="instrument-panel rounded-2xl p-4"
      data-testid="homepage-pins"
      aria-label="Pinned work"
    >
      <div className="flex items-start gap-2">
        <Pin className="mt-0.5 h-3.5 w-3.5 text-primary" aria-hidden />
        <p className="text-sm font-semibold">Pinned</p>
      </div>
      {degradedReason ? (
        <p
          className="mt-3 rounded-md border border-warning/40 bg-warning/10 p-3 text-xs text-warning"
          role="status"
        >
          {degradedReason}
        </p>
      ) : null}
      {pins.length ? (
        <ol className="mt-3 space-y-1">
          {pins.slice(0, 4).map((pin) => (
            <li key={pin.id}>
              <Link
                href={pin.href}
                className="group flex items-start gap-2.5 rounded-lg p-2 transition-colors hover:bg-muted/50"
              >
                <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md bg-muted text-muted-foreground">
                  <ChartNoAxesColumn className="h-3 w-3" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium">
                    {pin.title}
                  </span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-[0.65rem] text-muted-foreground">
                    <span>{pinSourceLabel(pin.source_type)}</span>
                    <span aria-hidden>·</span>
                    <Clock3 className="h-2.5 w-2.5" aria-hidden />
                    <span>
                      {new Date(pin.created_at).toLocaleDateString("en", {
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </span>
                </span>
                <ExternalLink
                  className="mt-1 h-3 w-3 text-muted-foreground transition-colors group-hover:text-foreground"
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
): string | null {
  return agents[0]?.workspace_id || workspaces[0]?.id || null;
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
  // Forward the studio session cookie as the cp bearer for SSR.
  const token = getCpAccessToken();
  const auth = token ? { token } : {};
  const { workspaces, degraded_reason: workspacesDegradedReason } =
    await listWorkspaces(auth).catch((error: unknown) => ({
      workspaces: [],
      degraded_reason:
        error instanceof Error
          ? error.message
          : "Could not load workspace context.",
    }));
  const initialWorkspaceId = resolveHomeWorkspaceId([], workspaces);
  const agentsResult = initialWorkspaceId
    ? await listAgents({ ...auth, workspaceId: initialWorkspaceId })
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
  const workspaceId = resolveHomeWorkspaceId(agents, workspaces);
  const activeWorkspace =
    workspaces.find((workspace) => workspace.id === workspaceId) ??
    workspaces[0] ??
    null;
  const contextWarnings = homeContextWarnings(
    agentsDegradedReason,
    workspacesDegradedReason,
  );
  const estateHealth = await fetchEstateHealth(workspaceId, {
    fallbackAgents: agents,
  });
  const homepagePins = await fetchHomepagePins(workspaceId);

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-6 p-5 lg:grid-cols-[minmax(0,1fr)_18rem] lg:p-8">
      <div className="min-w-0">
        <EstateOverview health={estateHealth} />
      </div>

      <aside className="grid content-start gap-4" aria-label="Primary actions">
        <div className="instrument-panel rounded-2xl p-4">
          <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Compose
          </p>
          <p className="mt-2 text-sm font-semibold leading-tight">
            Start a new agent.
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Define what it should do before it talks to anyone.
          </p>
          {/* Per-source 401 / unavailable notices are intentionally not
              repeated here. The "cp-api unavailable" chip + single
              notice in the estate header carries the same signal; this
              card is for the Compose action, not for diagnosing
              connectivity. The test hook stays in the DOM for tooling
              that asserts on it, but it's hidden when collapsed. */}
          {contextWarnings.length > 0 ? (
            <span
              className="sr-only"
              data-testid="home-context-degraded"
              role="status"
            >
              {contextWarnings.join(" ")}
            </span>
          ) : null}
          <div className="mt-4 flex flex-col gap-2">
            <NewAgentModal
              existingSlugs={existingSlugs}
              workspaceId={workspaceId}
              workspaceName={activeWorkspace?.name}
              workspaceRole={activeWorkspace?.role}
            />
            <Link
              href="/migrate"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <PackageOpen className="mr-2 h-3.5 w-3.5" aria-hidden />
              Import agent
            </Link>
          </div>
        </div>

        <div className="instrument-panel rounded-2xl p-2">
          <p className="px-2 pb-1 pt-1.5 text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Routes
          </p>
          <div className="space-y-0.5">
            <RouteLink
              href="/agents"
              title="Your agents"
              detail="Every agent in this workspace."
              icon={Bot}
            />
            <RouteLink
              href="/evals"
              title="Evals"
              detail="Turn real conversations into tests."
              icon={TestTube2}
            />
            <RouteLink
              href="/deploys"
              title="Deploys"
              detail="Candidates, approvals, and rollback."
              icon={GitPullRequestArrow}
            />
            <RouteLink
              href="/inbox"
              title="Human inbox"
              detail="Where humans step in — and the agent learns from it."
              icon={Inbox}
            />
          </div>
        </div>

        <PinnedWork
          pins={homepagePins.items}
          degradedReason={homepagePins.degradedReason}
        />
      </aside>
    </main>
  );
}

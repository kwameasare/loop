import Link from "next/link";
import {
  Bot,
  GitPullRequestArrow,
  Inbox,
  PackageOpen,
  TestTube2,
} from "lucide-react";

import { NewAgentModal } from "@/components/agents/new-agent-modal";
import { EstateOverview } from "@/components/estate/estate-overview";
import { buttonVariants } from "@/components/ui/button";
import { listAgents, type AgentSummary } from "@/lib/cp-api";
import { fetchEstateHealth } from "@/lib/estate-health";
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

export function resolveHomeWorkspaceId(
  agents: readonly AgentSummary[],
  workspaces: readonly Workspace[],
  fallback: string | undefined = process.env.LOOP_DEFAULT_WORKSPACE_ID,
): string | null {
  return agents[0]?.workspace_id || workspaces[0]?.id || fallback || null;
}

export default async function HomePage() {
  const { agents } = await listAgents().catch(() => ({ agents: [] }));
  const { workspaces } = await listWorkspaces().catch(() => ({
    workspaces: [],
  }));
  const existingSlugs = agents.map((agent) => agent.slug).filter(Boolean);
  const workspaceId = resolveHomeWorkspaceId(agents, workspaces);
  const estateHealth = await fetchEstateHealth(workspaceId, {
    fallbackAgents: agents,
  });

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
          <div className="mt-4 flex flex-col gap-2">
            <NewAgentModal
              existingSlugs={existingSlugs}
              workspaceId={workspaceId}
            />
            <Link
              href="/migrate"
              className={buttonVariants({ variant: "outline" })}
            >
              <PackageOpen className="mr-2 h-4 w-4" aria-hidden />
              Import agent
            </Link>
          </div>
        </div>

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

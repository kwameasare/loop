import Link from "next/link";
import { Search } from "lucide-react";
import { Suspense } from "react";

import { LiveBadge } from "@/components/target";
import { UserMenu } from "@/components/shell/user-menu";
import { WorkspaceMembersLink } from "@/components/shell/workspace-members-link";
import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";
import { targetUxFixtures } from "@/lib/target-ux";

function ContextChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="hidden h-8 items-center gap-1 rounded-md border bg-card px-2 text-xs md:inline-flex">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </span>
  );
}

export function Topbar() {
  const workspace = targetUxFixtures.workspace;
  const agent = targetUxFixtures.agents.find(
    (item) => item.id === workspace.activeAgentId,
  );
  return (
    <header
      className="sticky top-0 z-20 flex min-h-14 items-center justify-between gap-3 border-b bg-background/95 px-4 py-2 backdrop-blur"
      data-testid="topbar"
    >
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <Link href="/" className="text-sm font-semibold tracking-tight">
          Loop Studio
        </Link>
        <Suspense
          fallback={<div className="h-8 w-44 rounded-md bg-muted" aria-hidden="true" />}
        >
          <WorkspaceSwitcher />
          <WorkspaceMembersLink />
        </Suspense>
        <ContextChip label="Agent" value={agent?.name ?? "No agent"} />
        <ContextChip label="Env" value={workspace.environment} />
        <ContextChip label="Branch" value={workspace.branch} />
        <LiveBadge tone="draft" className="hidden h-8 md:inline-flex">
          {workspace.objectState}
        </LiveBadge>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <button
          type="button"
          className="inline-flex h-9 items-center gap-2 rounded-md border bg-card px-3 text-sm font-medium text-muted-foreground transition-colors duration-swift ease-standard hover:text-foreground"
        >
          <Search className="h-4 w-4" aria-hidden={true} />
          <span className="hidden sm:inline">Command</span>
          <kbd className="hidden rounded bg-muted px-1.5 py-0.5 text-[0.68rem] font-medium text-muted-foreground lg:inline">
            K
          </kbd>
        </button>
        <UserMenu />
      </div>
    </header>
  );
}

import Link from "next/link";
import { Suspense } from "react";

import { CommandPaletteLauncher } from "@/components/command";
import { PairDebugAudioControl } from "@/components/collaboration/pair-debug-audio-control";
import { HelpClipLauncher } from "@/components/help";
import { ActivityRibbon } from "@/components/shell/activity-ribbon";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { LiveBadge } from "@/components/target";
import { UserMenu } from "@/components/shell/user-menu";
import { WorkspaceMembersLink } from "@/components/shell/workspace-members-link";
import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";
import { FIXTURE_PRESENCE } from "@/lib/collaboration";
import { targetUxFixtures } from "@/lib/target-ux";

function ContextChip({ label, value }: { label: string; value: string }) {
  return (
    <span className="interactive-lift hidden h-8 items-center gap-1 rounded-md border bg-card/70 px-2 text-xs shadow-sm backdrop-blur md:inline-flex">
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
      className="sticky top-0 z-20 flex min-h-14 items-center justify-between gap-3 border-b bg-background/82 px-4 py-2 shadow-sm backdrop-blur-xl"
      data-testid="topbar"
    >
      <ActivityRibbon />
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        <Link
          href="/"
          className="group inline-flex items-center gap-2 text-sm font-semibold tracking-tight"
        >
          <span className="grid h-8 w-8 place-items-center rounded-md border bg-primary text-primary-foreground shadow-sm transition-transform duration-swift ease-standard group-hover:-rotate-3">
            L
          </span>
          <span>Studio</span>
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
        <PairDebugAudioControl
          workspaceId={workspace.id}
          agentId={workspace.activeAgentId}
          teammateCount={Math.max(0, FIXTURE_PRESENCE.length - 1)}
          participantId="builder:local"
        />
        <ThemeToggle />
        <HelpClipLauncher />
        <CommandPaletteLauncher />
        <UserMenu />
      </div>
    </header>
  );
}

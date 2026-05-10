"use client";

import Link from "next/link";
import { Suspense } from "react";
import { usePathname } from "next/navigation";

import { CommandPaletteLauncher } from "@/components/command";
import { PairDebugAudioControl } from "@/components/collaboration/pair-debug-audio-control";
import { HelpClipLauncher } from "@/components/help";
import { ActivityRibbon } from "@/components/shell/activity-ribbon";
import { ThemeToggle } from "@/components/shell/theme-toggle";
import { UserMenu } from "@/components/shell/user-menu";
import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";
import { useActiveWorkspace } from "@/lib/use-active-workspace";
import { usePresenceSocket } from "@/lib/use-presence-socket";
import { useUser } from "@/lib/use-user";

function routeContext(pathname: string | null): {
  agentId: string | null;
  section: string;
} {
  if (!pathname) return { agentId: null, section: "Workspace" };
  const agentMatch = pathname.match(/^\/agents\/([^/]+)/);
  if (agentMatch?.[1]) {
    return {
      agentId: decodeURIComponent(agentMatch[1]),
      section: "Agent workbench",
    };
  }
  const [segment = ""] = pathname.split("/").filter(Boolean);
  const labels: Record<string, string> = {
    agents: "Agent registry",
    evals: "Eval Foundry",
    replay: "Replay",
    traces: "Trace Theater",
    observe: "Observatory",
    inbox: "HITL Inbox",
    channels: "Channels",
    voice: "Voice channel stage",
    scenes: "Scenes",
    marketplace: "Marketplace",
    migrate: "Migration Atelier",
    enterprise: "Governance",
    costs: "Costs",
    billing: "Billing",
  };
  return { agentId: null, section: labels[segment] ?? "Workspace" };
}

function shortId(value: string): string {
  return value.length <= 10 ? value : `${value.slice(0, 8)}...`;
}

function ContextChip({
  label,
  value,
  href,
}: {
  label: string;
  value: string;
  href?: string;
}) {
  const body = (
    <>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </>
  );
  if (href) {
    return (
      <Link
        href={href}
        className="interactive-lift hidden h-8 items-center gap-1 rounded-md border bg-card/70 px-2 text-xs shadow-sm backdrop-blur transition-colors hover:bg-muted/70 md:inline-flex"
      >
        {body}
      </Link>
    );
  }
  return (
    <span className="interactive-lift hidden h-8 items-center gap-1 rounded-md border bg-card/70 px-2 text-xs shadow-sm backdrop-blur md:inline-flex">
      {body}
    </span>
  );
}

function TopbarPairDebugAudio({ agentId }: { agentId: string | null }) {
  const { active } = useActiveWorkspace();
  const { user, isAuthenticated, isLoading } = useUser();
  const callerSub = user?.sub ?? "";
  const display = user?.name ?? user?.email ?? user?.sub ?? "Builder";
  const focus = agentId ? `agent/${agentId}` : undefined;
  const shouldConnect = Boolean(
    agentId && active?.id && callerSub && isAuthenticated && !isLoading,
  );
  const presence = usePresenceSocket({
    workspaceId: shouldConnect ? active?.id : undefined,
    callerSub: callerSub || "anonymous",
    display,
    focus,
    enabled: shouldConnect,
  });
  const teammateCount = presence.users.filter(
    (presenceUser) =>
      presenceUser.id !== callerSub && presenceUser.focus === focus,
  ).length;

  if (!agentId || !active?.id || !callerSub || teammateCount === 0) {
    return null;
  }

  return (
    <div data-testid="topbar-pair-debug-audio">
      <PairDebugAudioControl
        workspaceId={active.id}
        agentId={agentId}
        teammateCount={teammateCount}
        participantId={callerSub}
      />
    </div>
  );
}

export function Topbar() {
  const pathname = usePathname();
  const context = routeContext(pathname);
  return (
    <header
      className="sticky top-0 z-20 flex min-h-14 items-center justify-between gap-3 border-b bg-background/84 px-4 py-2 shadow-sm backdrop-blur-xl"
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
          fallback={
            <div className="h-8 w-44 rounded-md bg-muted" aria-hidden="true" />
          }
        >
          <WorkspaceSwitcher />
        </Suspense>
        <ContextChip label="Surface" value={context.section} />
        {context.agentId ? (
          <ContextChip
            label="Agent"
            value={shortId(context.agentId)}
            href={`/agents/${encodeURIComponent(context.agentId)}`}
          />
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <Suspense fallback={null}>
          <TopbarPairDebugAudio agentId={context.agentId} />
        </Suspense>
        <ThemeToggle />
        <HelpClipLauncher />
        <CommandPaletteLauncher />
        <UserMenu />
      </div>
    </header>
  );
}

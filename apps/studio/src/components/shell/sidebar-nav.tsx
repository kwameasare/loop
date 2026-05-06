"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  Brain,
  CircleDollarSign,
  ClipboardCheck,
  GitBranch,
  Gauge,
  History,
  Inbox,
  KeyRound,
  MemoryStick,
  MessagesSquare,
  PackageOpen,
  Rocket,
  Route,
  ShieldCheck,
  Sparkles,
  TestTube2,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { LiveBadge } from "@/components/target";
import { cn } from "@/lib/utils";

export interface NavItem {
  id: string;
  href: string;
  label: string;
  summary: string;
  icon: LucideIcon;
  signal?: string;
}

export interface NavSection {
  id: "build" | "test" | "ship" | "observe" | "migrate" | "govern";
  label: string;
  items: readonly NavItem[];
}

export const NAV_SECTIONS: readonly NavSection[] = [
  {
    id: "build",
    label: "Build",
    items: [
      {
        id: "agents",
        href: "/agents",
        label: "Agents",
        summary: "Workbench, behavior, tools, knowledge, memory",
        icon: Sparkles,
        signal: "draft",
      },
      {
        id: "tools",
        href: "/agents?surface=tools",
        label: "Tools",
        summary: "Contracts, mocks, auth, side effects",
        icon: Wrench,
      },
      {
        id: "memory",
        href: "/agents?surface=memory",
        label: "Memory",
        summary: "Fact writes, policies, safety flags",
        icon: MemoryStick,
      },
    ],
  },
  {
    id: "test",
    label: "Test",
    items: [
      {
        id: "evals",
        href: "/evals",
        label: "Evals",
        summary: "Suites, judges, production-derived coverage",
        icon: TestTube2,
      },
      {
        id: "replay",
        href: "/traces?mode=replay",
        label: "Replay",
        summary: "Replay conversations against drafts",
        icon: History,
      },
      {
        id: "simulator",
        href: "/agents?surface=simulator",
        label: "Simulator",
        summary: "Channel preview and slash commands",
        icon: MessagesSquare,
      },
    ],
  },
  {
    id: "ship",
    label: "Ship",
    items: [
      {
        id: "deploys",
        href: "/agents?surface=deploys",
        label: "Deploys",
        summary: "Preflight, canary, rollback, approvals",
        icon: Rocket,
        signal: "canary",
      },
      {
        id: "versions",
        href: "/agents?surface=versions",
        label: "Versions",
        summary: "Snapshots, branches, behavioral diff",
        icon: GitBranch,
      },
      {
        id: "billing",
        href: "/billing",
        label: "Billing",
        summary: "Plan, invoices, limits",
        icon: CircleDollarSign,
      },
    ],
  },
  {
    id: "observe",
    label: "Observe",
    items: [
      {
        id: "traces",
        href: "/traces",
        label: "Traces",
        summary: "Scrubber, spans, forks, x-ray evidence",
        icon: Route,
      },
      {
        id: "inbox",
        href: "/inbox",
        label: "Inbox",
        summary: "Human handoff and operator actions",
        icon: Inbox,
        signal: "live",
      },
      {
        id: "costs",
        href: "/costs",
        label: "Costs",
        summary: "Latency budget, spend, optimization",
        icon: Gauge,
      },
    ],
  },
  {
    id: "migrate",
    label: "Migrate",
    items: [
      {
        id: "import",
        href: "/migrate",
        label: "Import",
        summary: "Botpress and legacy platform intake",
        icon: PackageOpen,
      },
      {
        id: "parity",
        href: "/migrate#three-pane-review-heading",
        label: "Parity",
        summary: "Structure, behavior, cost, risk comparison",
        icon: ClipboardCheck,
      },
      {
        id: "lineage",
        href: "/traces?mode=lineage",
        label: "Lineage",
        summary: "Persistent import evidence after cutover",
        icon: Boxes,
      },
    ],
  },
  {
    id: "govern",
    label: "Govern",
    items: [
      {
        id: "enterprise",
        href: "/enterprise",
        label: "Enterprise",
        summary: "SSO, SCIM, residency, evidence packs",
        icon: ShieldCheck,
      },
      {
        id: "members",
        href: "/workspaces/enterprise",
        label: "Members",
        summary: "Roles, groups, approvals",
        icon: KeyRound,
      },
      {
        id: "policies",
        href: "/enterprise",
        label: "Policies",
        summary: "Workspace rules and audit evidence",
        icon: Brain,
      },
    ],
  },
];

export const NAV_ITEMS: readonly NavItem[] = NAV_SECTIONS.flatMap(
  (section) => section.items,
);

function isActive(current: string | null, href: string): boolean {
  if (!current) return false;
  if (current === href) return true;
  return current.startsWith(`${href}/`);
}

export function SidebarNav() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Canonical Studio IA"
      className="flex h-full flex-col gap-4 overflow-y-auto p-3"
      data-testid="sidebar-nav"
    >
      <div className="px-2 py-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Loop
        </p>
        <p className="mt-1 text-sm font-semibold tracking-tight">Studio</p>
      </div>
      {NAV_SECTIONS.map((section) => (
        <section
          key={section.id}
          aria-labelledby={`nav-section-${section.id}`}
          data-testid={`nav-section-${section.id}`}
          className="space-y-1"
        >
          <h2
            id={`nav-section-${section.id}`}
            className="px-2 text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground"
          >
            {section.label}
          </h2>
          {section.items.map((item) => {
            const active = isActive(pathname, item.href);
            const Icon = item.icon;
            return (
              <Link
                key={`${section.id}-${item.id}`}
                href={item.href}
                data-testid={`nav-${item.id}`}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group flex min-h-12 items-start gap-2 rounded-md border border-transparent px-2.5 py-2 text-sm transition-colors duration-swift ease-standard",
                  active
                    ? "border-border bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )}
              >
                <Icon
                  className="mt-0.5 h-4 w-4 shrink-0"
                  aria-hidden={true}
                />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-medium leading-5">{item.label}</span>
                    {item.signal ? (
                      <LiveBadge
                        tone={item.signal === "canary" ? "canary" : item.signal === "live" ? "live" : "draft"}
                        className="h-5 px-1.5 text-[0.65rem]"
                      >
                        {item.signal}
                      </LiveBadge>
                    ) : null}
                  </span>
                  <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                    {item.summary}
                  </span>
                </span>
              </Link>
            );
          })}
        </section>
      ))}
    </nav>
  );
}

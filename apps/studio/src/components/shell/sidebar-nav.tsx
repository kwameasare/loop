"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  Brain,
  ChevronDown,
  ChevronRight,
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
import { useState } from "react";

import { LiveBadge } from "@/components/target";
import { targetUxFixtures } from "@/lib/target-ux";
import { cn } from "@/lib/utils";

export interface NavItem {
  id: string;
  href: string;
  label: string;
  summary: string;
  icon: LucideIcon;
  signal?: string;
  children?: readonly NavItem[];
}

export interface NavSection {
  id: "build" | "test" | "ship" | "observe" | "migrate" | "govern";
  label: string;
  items: readonly NavItem[];
}

const ACTIVE_AGENT_ID = targetUxFixtures.workspace.activeAgentId;

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
        children: [
          {
            id: "tools",
            href: `/agents/${ACTIVE_AGENT_ID}/tools`,
            label: "Tools",
            summary: "Contracts, mocks, auth, side effects",
            icon: Wrench,
          },
          {
            id: "knowledge",
            href: `/agents/${ACTIVE_AGENT_ID}/kb`,
            label: "Knowledge",
            summary: "Retrieval, inverse lab, embeddings",
            icon: Brain,
          },
          {
            id: "memory",
            href: `/agents/${ACTIVE_AGENT_ID}/memory`,
            label: "Memory",
            summary: "Fact writes, policies, safety flags",
            icon: MemoryStick,
          },
          {
            id: "simulator",
            href: `/agents/${ACTIVE_AGENT_ID}/simulator`,
            label: "Simulator",
            summary: "Channel preview and slash commands",
            icon: MessagesSquare,
          },
        ],
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
        href: "/replay",
        label: "Replay",
        summary: "Replay conversations against drafts",
        icon: History,
      },
      {
        id: "scenarios",
        href: "/scenarios",
        label: "Scenarios",
        summary: "North-star validation journeys",
        icon: ClipboardCheck,
      },
    ],
  },
  {
    id: "ship",
    label: "Ship",
    items: [
      {
        id: "deploys",
        href: `/agents/${ACTIVE_AGENT_ID}/deploys`,
        label: "Deploys",
        summary: "Preflight, canary, rollback, approvals",
        icon: Rocket,
        signal: "canary",
      },
      {
        id: "versions",
        href: `/agents/${ACTIVE_AGENT_ID}/versions`,
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
        id: "observatory",
        href: "/observe",
        label: "Observatory",
        summary: "Health, anomalies, production tail",
        icon: Gauge,
        signal: "live",
      },
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
        icon: CircleDollarSign,
      },
      {
        id: "voice",
        href: "/voice",
        label: "Voice",
        summary: "ASR, TTS, barge-in, voice evals",
        icon: MessagesSquare,
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
        href: "/migrate/parity",
        label: "Parity",
        summary: "Structure, behavior, cost, risk comparison",
        icon: ClipboardCheck,
      },
      {
        id: "lineage",
        href: "/migrate/parity",
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

export const NAV_ITEMS: readonly NavItem[] = NAV_SECTIONS.flatMap((section) =>
  section.items.flatMap((item) => [item, ...(item.children ?? [])]),
);

function isActive(current: string | null, href: string): boolean {
  if (!current) return false;
  const cleanHref = href.split(/[?#]/)[0] || "/";
  if (current === cleanHref) return true;
  return cleanHref !== "/" && current.startsWith(`${cleanHref}/`);
}

export function SidebarNav() {
  const pathname = usePathname();
  const [openSections, setOpenSections] =
    useState<Record<NavSection["id"], boolean>>({
      build: true,
      test: true,
      ship: true,
      observe: true,
      migrate: true,
      govern: true,
    });
  return (
    <nav
      aria-label="Canonical Studio IA"
      className="flex h-full flex-col gap-3 overflow-y-auto p-3"
      data-testid="sidebar-nav"
    >
      <div className="rounded-md border bg-background p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Loop
            </p>
            <p className="mt-1 text-sm font-semibold tracking-tight">Studio</p>
          </div>
          <LiveBadge tone="live" className="h-6 px-2 text-[0.65rem]">
            canonical
          </LiveBadge>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Build, Test, Ship, Observe, Migrate, Govern.
        </p>
      </div>
      {NAV_SECTIONS.map((section) => (
        <section
          key={section.id}
          aria-labelledby={`nav-section-${section.id}`}
          data-testid={`nav-section-${section.id}`}
          className="rounded-md border border-transparent"
        >
          <button
            type="button"
            id={`nav-section-${section.id}`}
            className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground transition-colors hover:bg-muted"
            aria-expanded={openSections[section.id]}
            onClick={() =>
              setOpenSections((current) => ({
                ...current,
                [section.id]: !current[section.id],
              }))
            }
          >
            <span>{section.label}</span>
            {openSections[section.id] ? (
              <ChevronDown className="h-3.5 w-3.5" aria-hidden={true} />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" aria-hidden={true} />
            )}
          </button>
          {openSections[section.id] ? (
            <div className="mt-1 space-y-1">
              {section.items.map((item) => (
                <NavLink
                  key={`${section.id}-${item.id}`}
                  item={item}
                  pathname={pathname}
                />
              ))}
            </div>
          ) : null}
        </section>
      ))}
    </nav>
  );
}

function NavLink({
  item,
  pathname,
  depth = 0,
}: {
  item: NavItem;
  pathname: string | null;
  depth?: number;
}) {
  const active = isActive(pathname, item.href);
  const childActive = item.children?.some((child) => isActive(pathname, child.href)) ?? false;
  const Icon = item.icon;
  return (
    <div>
      <Link
        href={item.href}
        data-testid={`nav-${item.id}`}
        aria-current={active ? "page" : undefined}
        className={cn(
          "group flex min-h-12 items-start gap-2 rounded-md border border-transparent px-2.5 py-2 text-sm transition-all duration-swift ease-standard hover:-translate-y-px",
          depth > 0 && "ml-6 min-h-10 border-l pl-3",
          active || childActive
            ? "border-border bg-accent text-accent-foreground shadow-sm"
            : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        )}
      >
        <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden={true} />
        <span className="min-w-0 flex-1">
          <span className="flex items-center justify-between gap-2">
            <span className="font-medium leading-5">{item.label}</span>
            {item.signal ? (
              <LiveBadge
                tone={
                  item.signal === "canary"
                    ? "canary"
                    : item.signal === "live"
                      ? "live"
                      : "draft"
                }
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
      {item.children ? (
        <div className="mt-1 space-y-1">
          {item.children.map((child) => (
            <NavLink
              key={`${item.id}-${child.id}`}
              item={child}
              pathname={pathname}
              depth={depth + 1}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

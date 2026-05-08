"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Building2,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  FileSearch,
  GitBranch,
  Gauge,
  History,
  Inbox,
  MessagesSquare,
  PackageOpen,
  Radar,
  Rocket,
  Route,
  ShieldCheck,
  Sparkles,
  Store,
  TestTube2,
  Users,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { AgentMoodRing } from "@/components/shell/agent-mood-ring";
import { LiveBadge } from "@/components/target";
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

function agentIdFromPath(pathname: string | null): string | null {
  if (!pathname) return null;
  const match = pathname.match(/^\/agents\/([^/]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function agentHref(agentId: string | null, segment: string): string {
  if (!agentId) return "/agents";
  return segment
    ? `/agents/${encodeURIComponent(agentId)}/${segment}`
    : `/agents/${encodeURIComponent(agentId)}`;
}

export function buildNavSections(
  agentId: string | null = null,
): readonly NavSection[] {
  return [
    {
      id: "build",
      label: "Build",
      items: [
        {
          id: "agents",
          href: "/agents",
          label: "Agent Workbench",
          summary: "Profile, behavior, tools, knowledge, memory, deploy",
          icon: Bot,
        },
        {
          id: "channels",
          href: "/channels",
          label: "Channels",
          summary: "Web, WhatsApp, Telegram, Slack, SMS, email, voice",
          icon: MessagesSquare,
        },
        {
          id: "marketplace",
          href: "/marketplace",
          label: "Marketplace",
          summary: "Install and publish workspace skills",
          icon: Store,
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
      ],
    },
    {
      id: "ship",
      label: "Ship",
      items: [
        {
          id: "deploys",
          href: agentId ? agentHref(agentId, "deploys") : "/deploys",
          label: "Deploys",
          summary: "Preflight, canary, rollback, approvals",
          icon: Rocket,
        },
        ...(agentId
          ? [
              {
                id: "versions",
                href: agentHref(agentId, "versions"),
                label: "Versions",
                summary: "Snapshots, branches, behavioral diff",
                icon: GitBranch,
              },
            ]
          : []),
        {
          id: "money",
          href: "/costs",
          label: "Costs & Billing",
          summary: "Operational spend, plan, invoices, limits",
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
        },
        {
          id: "traces",
          href: "/traces",
          label: "Traces",
          summary: "Scrubber, spans, forks, x-ray evidence",
          icon: Route,
        },
        {
          id: "xray",
          href: "/xray",
          label: "Behavior Evidence",
          summary: "Observed behavior, dead context, evidence",
          icon: Radar,
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
          icon: Radar,
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
          icon: Building2,
        },
        {
          id: "members",
          href: "/workspaces/enterprise/members",
          label: "Members",
          summary: "Roles, groups, approvals",
          icon: Users,
        },
        {
          id: "policies",
          href: "/enterprise/govern",
          label: "Policies",
          summary: "Workspace rules and audit evidence",
          icon: ShieldCheck,
        },
        {
          id: "audit",
          href: "/enterprise/audit",
          label: "Audit",
          summary: "Append-only evidence and filters",
          icon: FileSearch,
        },
      ],
    },
  ];
}

export const NAV_SECTIONS: readonly NavSection[] = buildNavSections();

export const NAV_ITEMS: readonly NavItem[] = NAV_SECTIONS.flatMap((section) =>
  section.items.flatMap((item) => [item, ...(item.children ?? [])]),
);

function isActive(current: string | null, href: string): boolean {
  if (!current) return false;
  const cleanHref = href.split(/[?#]/)[0] || "/";
  if (current === cleanHref) return true;
  return cleanHref !== "/" && current.startsWith(`${cleanHref}/`);
}

function sectionIsActive(
  pathname: string | null,
  section: NavSection,
): boolean {
  return section.items.some(
    (item) =>
      isActive(pathname, item.href) ||
      (item.children?.some((child) => isActive(pathname, child.href)) ?? false),
  );
}

function initialOpenSections(
  pathname: string | null,
  sections: readonly NavSection[],
): Record<NavSection["id"], boolean> {
  return sections.reduce(
    (acc, section) => {
      acc[section.id] =
        section.id === "build" || sectionIsActive(pathname, section);
      return acc;
    },
    {} as Record<NavSection["id"], boolean>,
  );
}

export function SidebarNav() {
  const pathname = usePathname();
  const activeAgentId = agentIdFromPath(pathname);
  const navSections = useMemo(
    () => buildNavSections(activeAgentId),
    [activeAgentId],
  );
  const [openSections, setOpenSections] = useState<
    Record<NavSection["id"], boolean>
  >(() => initialOpenSections(pathname, navSections));

  useEffect(() => {
    setOpenSections((current) => {
      const next = { ...current };
      for (const section of navSections) {
        if (sectionIsActive(pathname, section)) next[section.id] = true;
      }
      return next;
    });
  }, [navSections, pathname]);

  return (
    <nav
      aria-label="Studio IA"
      className="quiet-scrollbar flex h-full flex-col gap-3 overflow-y-auto p-3"
      data-testid="sidebar-nav"
    >
      <div className="instrument-panel rounded-md p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Loop
            </p>
            <p className="mt-1 text-base font-semibold tracking-tight">
              Studio
            </p>
          </div>
          <span className="rounded-md border bg-background/70 px-2 py-1 text-[0.65rem] font-semibold uppercase tracking-wide text-muted-foreground">
            agent ops
          </span>
        </div>
        <div className="mt-3 grid grid-cols-6 gap-1" aria-hidden="true">
          {navSections.map((section) => (
            <span
              key={section.id}
              className={cn(
                "h-1 rounded-full transition-colors duration-swift",
                sectionIsActive(pathname, section) ? "bg-primary" : "bg-muted",
              )}
            />
          ))}
        </div>
      </div>
      <div
        className="rounded-md border bg-card/70 p-2"
        data-testid="nav-attention"
      >
        <NavLink
          item={{
            id: "inbox",
            href: "/inbox",
            label: "HITL Inbox",
            summary: "Human intervention, approvals, unresolved turns",
            icon: Inbox,
          }}
          pathname={pathname}
        />
      </div>
      {activeAgentId ? (
        <div
          className="rounded-md border bg-card/70 p-2"
          data-testid="nav-active-agent"
        >
          <p className="px-2 pb-1 text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground">
            Active Agent
          </p>
          <NavLink
            item={{
              id: "active-agent",
              href: agentHref(activeAgentId, ""),
              label: "Workbench",
              summary: "Agent-scoped profile, behavior, tools, memory, tests",
              icon: Sparkles,
            }}
            pathname={pathname}
          />
        </div>
      ) : null}
      {navSections.map((section) => (
        <section
          key={section.id}
          aria-labelledby={`nav-section-${section.id}`}
          data-testid={`nav-section-${section.id}`}
          className="rounded-md border border-transparent"
        >
          <button
            type="button"
            id={`nav-section-${section.id}`}
            className="group flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[0.68rem] font-semibold uppercase tracking-wider text-muted-foreground transition-all duration-swift ease-standard hover:bg-muted/70 hover:text-foreground"
            aria-expanded={openSections[section.id]}
            onClick={() =>
              setOpenSections((current) => ({
                ...current,
                [section.id]: !current[section.id],
              }))
            }
          >
            <span className="flex items-center gap-2">
              <span>{section.label}</span>
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[0.6rem] tabular-nums text-muted-foreground group-hover:text-foreground">
                {section.items.length}
              </span>
            </span>
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
  const childActive =
    item.children?.some((child) => isActive(pathname, child.href)) ?? false;
  const Icon = item.icon;
  return (
    <div>
      <Link
        href={item.href}
        data-testid={`nav-${item.id}`}
        aria-current={active ? "page" : undefined}
        className={cn(
          "interactive-lift pressable group flex min-h-10 items-center gap-2 rounded-md border border-transparent px-2.5 py-2 text-sm",
          depth > 0 && "ml-5 min-h-9 border-l border-border/70 pl-3",
          active || childActive
            ? "border-border bg-accent/88 text-accent-foreground shadow-sm"
            : "text-muted-foreground hover:border-border/70 hover:bg-accent/50 hover:text-foreground",
        )}
      >
        {item.id === "agents" && depth === 0 ? (
          <AgentMoodRing label={item.label} mood="healthy" />
        ) : (
          <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden={true} />
        )}
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
          <span
            className={cn(
              "block max-h-0 overflow-hidden text-xs text-muted-foreground opacity-0 transition-all duration-swift ease-standard group-hover:mt-0.5 group-hover:max-h-5 group-hover:opacity-100 group-focus-visible:mt-0.5 group-focus-visible:max-h-5 group-focus-visible:opacity-100",
              (active || childActive) && "mt-0.5 max-h-5 truncate opacity-100",
            )}
          >
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

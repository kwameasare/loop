"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface AgentTabSpec {
  /** Path segment relative to /agents/{id} (empty string for overview). */
  segment: string;
  label: string;
  summary: string;
  group: "Define" | "Connect" | "Prove" | "Ship" | "Operate";
}

export const AGENT_TABS: AgentTabSpec[] = [
  {
    segment: "",
    label: "Overview",
    summary: "State and next work",
    group: "Define",
  },
  {
    segment: "contract",
    label: "Contract",
    summary: "Commitment document",
    group: "Define",
  },
  {
    segment: "behavior",
    label: "Behavior",
    summary: "Instructions and policy",
    group: "Define",
  },
  {
    segment: "channels",
    label: "Channels",
    summary: "Web, WhatsApp, Telegram, Slack, Teams, SMS, email, voice, webhook",
    group: "Connect",
  },
  {
    segment: "tools",
    label: "Tools",
    summary: "Sandbox and live contracts",
    group: "Connect",
  },
  {
    segment: "kb",
    label: "Knowledge",
    summary: "Sources and retrieval",
    group: "Connect",
  },
  {
    segment: "memory",
    label: "Memory",
    summary: "Retention and privacy",
    group: "Connect",
  },
  {
    segment: "simulator",
    label: "Simulations",
    summary: "Manual, scripted, and channel tests",
    group: "Prove",
  },
  {
    segment: "evals",
    label: "Evals",
    summary: "Coverage and gates",
    group: "Prove",
  },
  {
    segment: "traces",
    label: "Traces",
    summary: "Evidence and replay",
    group: "Prove",
  },
  {
    segment: "workflow",
    label: "Workflow",
    summary: "Branches and release path",
    group: "Ship",
  },
  {
    segment: "deploys",
    label: "Deployments",
    summary: "Preflight and rollout",
    group: "Ship",
  },
  {
    segment: "observe",
    label: "Observability",
    summary: "Health and incidents",
    group: "Operate",
  },
  {
    segment: "governance",
    label: "Governance",
    summary: "Approvals and audit",
    group: "Operate",
  },
  {
    segment: "history",
    label: "History",
    summary: "Handoff walkthrough",
    group: "Operate",
  },
];

const TAB_GROUPS: readonly AgentTabSpec["group"][] = [
  "Define",
  "Connect",
  "Prove",
  "Ship",
  "Operate",
];

export interface AgentTabsProps {
  agentId: string;
  /** Override for tests. */
  pathname?: string;
  orientation?: "horizontal" | "vertical";
}

/**
 * Tab navigation for the agent detail page. The active tab is derived
 * from the App Router pathname so deep links and back-button behaviour
 * stay consistent. Each tab is rendered as a real route segment, so
 * Next.js code-splits the tab content lazily on first navigation.
 */
export function AgentTabs({
  agentId,
  pathname,
  orientation = "horizontal",
}: AgentTabsProps) {
  const routePathname = usePathname();
  const currentRaw = pathname ?? routePathname ?? "";
  const base = `/agents/${agentId}`;
  const current = currentRaw.startsWith(base)
    ? (currentRaw.slice(base.length).replace(/^\//, "").split("/")[0] ?? "")
    : "";
  const tabGroups = TAB_GROUPS.map((group) => ({
    group,
    tabs: AGENT_TABS.filter((tab) => tab.group === group),
  })).filter(({ tabs }) => tabs.length > 0);
  return (
    <nav
      role="tablist"
      aria-label="Agent sections"
      data-testid="agent-tabs"
      aria-orientation={orientation}
      className={
        orientation === "vertical"
          ? "flex flex-col gap-1"
          : "flex flex-wrap gap-2"
      }
    >
      {tabGroups.map(({ group, tabs }) => (
        <div
          key={group}
          className={
            orientation === "vertical"
              ? "space-y-1"
              : "rounded-lg border bg-background/55 p-1 shadow-[inset_0_1px_0_hsl(var(--glass-hi)/0.4)]"
          }
          data-testid={`agent-tab-group-${group.toLowerCase()}`}
        >
          <p
            className={
              orientation === "vertical"
                ? "px-3 pt-2 text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground"
                : "sr-only"
            }
          >
            {group}
          </p>
          <div
            className={orientation === "vertical" ? "space-y-1" : "flex gap-1"}
          >
            {tabs.map((tab) => {
              const href = tab.segment ? `${base}/${tab.segment}` : base;
              const active = current === tab.segment;
              return (
                <Link
                  key={tab.segment || "overview"}
                  href={href}
                  role="tab"
                  aria-selected={active}
                  aria-current={active ? "page" : undefined}
                  data-testid={`agent-tab-${tab.segment || "overview"}`}
                  className={
                    orientation === "vertical"
                      ? "rounded-md border px-3 py-2 text-sm transition-colors " +
                        (active
                          ? "border-primary bg-primary/10 text-foreground"
                          : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground")
                      : "rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors " +
                        (active
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground")
                  }
                >
                  <span className="block font-medium">{tab.label}</span>
                  {orientation === "vertical" ? (
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      {tab.summary}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

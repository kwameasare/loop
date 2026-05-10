"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface AgentTabSpec {
  /** Path segment relative to /agents/{id} (empty string for overview). */
  segment: string;
  label: string;
  summary: string;
}

export const AGENT_TABS: AgentTabSpec[] = [
  { segment: "", label: "Overview", summary: "State and next work" },
  { segment: "contract", label: "Contract", summary: "Commitment document" },
  { segment: "behavior", label: "Behavior", summary: "Instructions and policy" },
  {
    segment: "channels",
    label: "Channels",
    summary: "Web, WhatsApp, Telegram, Slack, Teams, SMS, email, voice, webhook",
  },
  { segment: "tools", label: "Tools", summary: "Sandbox and live contracts" },
  { segment: "kb", label: "Knowledge", summary: "Sources and retrieval" },
  { segment: "memory", label: "Memory", summary: "Retention and privacy" },
  {
    segment: "simulator",
    label: "Simulations",
    summary: "Manual, scripted, and channel tests",
  },
  { segment: "evals", label: "Evals", summary: "Coverage and gates" },
  { segment: "traces", label: "Traces", summary: "Evidence and replay" },
  { segment: "workflow", label: "Workflow", summary: "Branches and release path" },
  { segment: "deploys", label: "Deployments", summary: "Preflight and rollout" },
  { segment: "observe", label: "Observability", summary: "Health and incidents" },
  { segment: "governance", label: "Governance", summary: "Approvals and audit" },
  { segment: "history", label: "History", summary: "Handoff walkthrough" },
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
  return (
    <nav
      role="tablist"
      aria-label="Agent sections"
      data-testid="agent-tabs"
      aria-orientation={orientation}
      className={
        orientation === "vertical"
          ? "flex flex-col gap-1"
          : "flex flex-wrap gap-1 border-b"
      }
    >
      {AGENT_TABS.map((tab) => {
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
                : "px-3 py-2 text-sm font-medium border-b-2 -mb-px " +
                  (active
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground")
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
    </nav>
  );
}

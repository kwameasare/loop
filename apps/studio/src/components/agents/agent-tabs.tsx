"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export interface AgentTabSpec {
  /** Path segment relative to /agents/{id} (empty string for overview). */
  segment: string;
  label: string;
}

export const AGENT_TABS: AgentTabSpec[] = [
  { segment: "", label: "Overview" },
  { segment: "behavior", label: "Behavior" },
  { segment: "map", label: "Map" },
  { segment: "versions", label: "Versions" },
  { segment: "channels", label: "Channels" },
  { segment: "tools", label: "Tools" },
  { segment: "kb", label: "Knowledge" },
  { segment: "deploys", label: "Deploys" },
  { segment: "secrets", label: "Secrets" },
];

export interface AgentTabsProps {
  agentId: string;
  /** Override for tests. */
  pathname?: string;
}

/**
 * Tab navigation for the agent detail page. The active tab is derived
 * from the App Router pathname so deep links and back-button behaviour
 * stay consistent. Each tab is rendered as a real route segment, so
 * Next.js code-splits the tab content lazily on first navigation.
 */
export function AgentTabs({ agentId, pathname }: AgentTabsProps) {
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
      className="flex flex-wrap gap-1 border-b"
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
              "px-3 py-2 text-sm font-medium border-b-2 -mb-px " +
              (active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground")
            }
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

import Link from "next/link";

import type { AgentSummary } from "@/lib/cp-api";

function versionLabel(agent: AgentSummary): string {
  return agent.active_version === null ? "draft" : `v${agent.active_version}`;
}

function stateLabel(agent: AgentSummary): string {
  return agent.object_state.replace(/_/g, " ");
}

function updatedLabel(agent: AgentSummary): string {
  if (!agent.updated_at) return "not recorded";
  try {
    return new Date(agent.updated_at).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return agent.updated_at;
  }
}

/**
 * Pure presentational list. Splitting the rendering away from the page's
 * data fetch keeps Vitest tests simple -- the test mounts AgentsList
 * directly with a fixture; the App Router page does the IO.
 */
export function AgentsList({ agents }: { agents: AgentSummary[] }) {
  if (agents.length === 0) {
    return (
      <p className="text-muted-foreground text-sm" data-testid="agents-empty">
        No agents yet. Create one in the studio to get started.
      </p>
    );
  }
  return (
    <ul
      className="divide-y divide-border rounded-md border"
      data-testid="agents-list"
    >
      {agents.map((agent) => (
        <li key={agent.id} className="p-0" data-testid="agents-item">
          <Link
            href={`/agents/${agent.id}`}
            className="grid gap-4 p-4 transition-colors hover:bg-muted/50 md:grid-cols-[minmax(0,1fr)_18rem]"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-medium">{agent.name}</h3>
                <span className="inline-flex items-center rounded-md border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {versionLabel(agent)}
                </span>
                <span
                  className="inline-flex items-center rounded-md border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground"
                  data-testid={`agent-state-${agent.id}`}
                >
                  {stateLabel(agent)}
                </span>
              </div>
              <p className="text-muted-foreground mt-1 text-sm">
                {agent.description || "No description yet."}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                slug: {agent.slug}
              </p>
            </div>
            <div className="min-w-0 rounded-md border bg-background p-3 text-xs text-muted-foreground">
              <p className="font-medium text-foreground">Current state</p>
              <p className="mt-1 line-clamp-2">{agent.state_reason}</p>
              <p className="mt-2 break-all font-mono">
                {agent.state_evidence_ref}
              </p>
              <p className="mt-2">Updated {updatedLabel(agent)}</p>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

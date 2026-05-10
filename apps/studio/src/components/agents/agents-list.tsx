import Link from "next/link";

import type { AgentSummary } from "@/lib/cp-api";
import { cn } from "@/lib/utils";

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

function ownerLabel(agent: AgentSummary): string {
  return agent.owner_user_id?.trim() || "Unassigned owner";
}

function backupOwnerLabel(agent: AgentSummary): string {
  return agent.backup_owner_user_id?.trim() || "No backup owner";
}

function healthLabel(agent: AgentSummary): string {
  return (agent.health_status ?? "unknown").replace(/_/g, " ");
}

function issueLabel(agent: AgentSummary): string {
  const count = agent.open_issue_count ?? 0;
  if (count === 0) return "No open issues";
  if (count === 1) return "1 open issue";
  return `${count} open issues`;
}

function healthClass(agent: AgentSummary): string {
  const status = agent.health_status ?? "";
  if (status === "needs_attention" || status === "blocked") {
    return "border-warning/40 bg-warning/10 text-warning";
  }
  if (status === "watching" || status === "ready_for_review") {
    return "border-info/40 bg-info/10 text-info";
  }
  return "border-border bg-muted text-muted-foreground";
}

/**
 * Pure presentational list. Splitting the rendering away from the page's
 * data fetch keeps Vitest tests simple -- the test mounts AgentsList
 * directly with a fixture; the App Router page does the IO.
 */
export function AgentsList({
  agents,
  degradedReason,
}: {
  agents: AgentSummary[];
  degradedReason?: string | undefined;
}) {
  if (agents.length === 0) {
    if (degradedReason) {
      return (
        <div
          className="rounded-md border border-warning/40 bg-warning/10 p-4 text-sm text-warning"
          data-testid="agents-degraded"
          role="status"
        >
          <p className="font-semibold">Agent registry is unavailable.</p>
          <p className="mt-1">{degradedReason}</p>
        </div>
      );
    }
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
            className="grid gap-4 p-4 transition-colors hover:bg-muted/50 lg:grid-cols-[minmax(0,1.4fr)_minmax(13rem,0.8fr)_minmax(15rem,1fr)]"
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="min-w-0 truncate text-base font-medium">
                  {agent.name}
                </h3>
                <span className="inline-flex items-center rounded-md border bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  {versionLabel(agent)}
                </span>
                <span
                  className="inline-flex items-center rounded-md border bg-background px-2 py-0.5 text-xs font-medium text-muted-foreground"
                  data-testid={`agent-state-${agent.id}`}
                >
                  {stateLabel(agent)}
                </span>
                <span
                  className={cn(
                    "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
                    healthClass(agent),
                  )}
                  data-testid={`agent-health-${agent.id}`}
                >
                  {healthLabel(agent)}
                </span>
              </div>
              <p className="text-muted-foreground mt-1 text-sm">
                {agent.description || "No description yet."}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                slug: {agent.slug}
              </p>
            </div>

            <div
              className="min-w-0 rounded-md border bg-background p-3 text-xs text-muted-foreground"
              data-testid={`agent-ownership-${agent.id}`}
            >
              <p className="font-medium text-foreground">Ownership</p>
              <p className="mt-1 truncate">{ownerLabel(agent)}</p>
              <p className="mt-1 truncate">{backupOwnerLabel(agent)}</p>
              <p className="mt-2 break-all font-mono">
                {agent.commitment_document_id ?? "commitment unavailable"}
              </p>
              <p className="mt-2">
                Contract {agent.commitment_status ?? "unknown"}
              </p>
            </div>

            <div
              className="min-w-0 rounded-md border bg-background p-3 text-xs text-muted-foreground"
              data-testid={`agent-operational-state-${agent.id}`}
            >
              <p className="font-medium text-foreground">Current state</p>
              <p className="mt-1 line-clamp-2">{agent.state_reason}</p>
              <p className="mt-2 break-all font-mono">
                {agent.state_evidence_ref}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                <span className="rounded-md bg-muted px-1.5 py-0.5">
                  env {agent.environment ?? stateLabel(agent)}
                </span>
                <span
                  className="rounded-md bg-muted px-1.5 py-0.5"
                  data-testid={`agent-open-issues-${agent.id}`}
                  title={(agent.open_issue_sources ?? []).join(", ")}
                >
                  {issueLabel(agent)}
                </span>
              </div>
              <p className="mt-2">Updated {updatedLabel(agent)}</p>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

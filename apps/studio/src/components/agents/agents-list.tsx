import Link from "next/link";
import { ArrowUpRight, Clock3, GitBranch, ShieldCheck } from "lucide-react";

import {
  AgentGlassOrb,
  type AgentGlassOrbState,
} from "@/components/agents/agent-glass-orb";
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

function healthChipClass(agent: AgentSummary): string {
  const status = agent.health_status ?? "";
  if (status === "needs_attention") return "status-chip--warning";
  if (status === "blocked") return "status-chip--danger";
  if (status === "watching" || status === "ready_for_review")
    return "status-chip--info";
  return "status-chip--success";
}

function orbState(agent: AgentSummary): AgentGlassOrbState {
  const status = agent.health_status ?? "";
  if (status === "needs_attention") return "drifting";
  if (status === "blocked") return "blocked";
  if (status === "watching" || status === "ready_for_review") return "watching";
  return "healthy";
}

/**
 * Constellation-style agent grid. Each card showcases the agent's hue orb
 * as the protagonist; meta is layered as light glass chips.
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
          className="notice notice--warning"
          data-testid="agents-degraded"
          role="status"
        >
          <div className="notice__body">
            <p className="notice__title">Agent registry is unavailable.</p>
            <p className="notice__detail">{degradedReason}</p>
          </div>
        </div>
      );
    }
    return (
      <div
        className="instrument-panel rounded-2xl p-6 text-sm text-muted-foreground"
        data-testid="agents-empty"
      >
        No agents yet. Create one in the studio to get started.
      </div>
    );
  }
  return (
    <ul
      className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"
      data-testid="agents-list"
    >
      {agents.map((agent) => (
        <li key={agent.id} data-testid="agents-item">
          <Link
            href={`/agents/${agent.id}`}
            className="instrument-panel interactive-lift group relative block overflow-hidden rounded-2xl p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <AgentGlassOrb
                agentId={agent.id}
                label={agent.name}
                size="lg"
                state={orbState(agent)}
              />
              <ArrowUpRight
                className="h-4 w-4 text-muted-foreground transition-transform duration-swift group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-foreground"
                aria-hidden
              />
            </div>
            <h3 className="relative z-10 mt-4 truncate text-lg font-semibold leading-tight">
              {agent.name}
            </h3>
            <p className="relative z-10 mt-0.5 font-mono text-[0.7rem] text-muted-foreground/80">
              slug: {agent.slug}
            </p>
            <p className="relative z-10 mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
              {agent.description || "No description yet."}
            </p>
            <div className="relative z-10 mt-4 flex flex-wrap gap-1.5">
              <span
                className={cn("status-chip", healthChipClass(agent))}
                data-testid={`agent-health-${agent.id}`}
              >
                <span className="status-chip__dot" />
                {healthLabel(agent)}
              </span>
              <span
                className="status-chip status-chip--neutral"
                data-testid={`agent-state-${agent.id}`}
              >
                {stateLabel(agent)}
              </span>
              <span className="status-chip status-chip--neutral">
                <GitBranch className="h-3 w-3" aria-hidden />
                {versionLabel(agent)}
              </span>
            </div>
            <dl className="relative z-10 mt-4 grid grid-cols-2 gap-3 text-xs">
              <div
                className="rounded-xl bg-muted/60 p-2.5 backdrop-blur-sm"
                data-testid={`agent-ownership-${agent.id}`}
              >
                <dt className="flex items-center gap-1.5 text-muted-foreground">
                  <ShieldCheck className="h-3 w-3" aria-hidden />
                  Owner
                </dt>
                <dd className="mt-1 truncate font-medium text-foreground">
                  {ownerLabel(agent)}
                </dd>
                <dd className="mt-0.5 truncate text-muted-foreground">
                  Backup · {backupOwnerLabel(agent)}
                </dd>
              </div>
              <div className="rounded-xl bg-muted/60 p-2.5 backdrop-blur-sm">
                <dt className="flex items-center gap-1.5 text-muted-foreground">
                  <Clock3 className="h-3 w-3" aria-hidden />
                  Updated
                </dt>
                <dd className="mt-1 font-medium text-foreground">
                  {updatedLabel(agent)}
                </dd>
                <dd
                  className="mt-0.5 truncate text-muted-foreground"
                  data-testid={`agent-open-issues-${agent.id}`}
                  title={(agent.open_issue_sources ?? []).join(", ")}
                >
                  {issueLabel(agent)}
                </dd>
              </div>
            </dl>
            <div
              className="relative z-10 mt-3 rounded-xl border border-border/60 bg-background/60 p-3 text-xs text-muted-foreground"
              data-testid={`agent-operational-state-${agent.id}`}
            >
              <p className="line-clamp-2 leading-5">{agent.state_reason}</p>
              <p className="mt-1.5 truncate font-mono text-[0.65rem] opacity-70">
                {agent.state_evidence_ref}
              </p>
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

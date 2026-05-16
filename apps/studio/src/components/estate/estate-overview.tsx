import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  ClipboardCheck,
  GitPullRequestArrow,
  Inbox,
  RadioTower,
  Rocket,
  ShieldCheck,
  TestTube2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type {
  EstateAttentionItem,
  EstateHealth,
  EstateHealthDataSource,
} from "@/lib/estate-health";
import { cn } from "@/lib/utils";

const SOURCE_LABEL: Record<EstateHealthDataSource, string> = {
  live: "Live cp-api",
  derived: "Derived from loaded agents",
  unconfigured: "No cp-api configured",
  unavailable: "cp-api unavailable",
};

function sourceChipClass(source: EstateHealthDataSource): string {
  if (source === "live") return "status-chip--success";
  if (source === "derived") return "status-chip--info";
  return "status-chip--warning";
}

function severityIcon(severity: EstateAttentionItem["severity"]): LucideIcon {
  if (severity === "critical") return AlertTriangle;
  if (severity === "watch") return RadioTower;
  return ShieldCheck;
}

function severityChip(severity: EstateAttentionItem["severity"]): string {
  if (severity === "critical") return "status-chip--warning";
  if (severity === "watch") return "status-chip--info";
  return "status-chip--success";
}

function severityRisk(risk: string): EstateAttentionItem["severity"] {
  if (risk === "critical" || risk === "high") return "critical";
  if (risk === "medium") return "watch";
  return "ready";
}

function MetricCell({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: number;
  detail: string;
  icon: LucideIcon;
}) {
  return (
    <div
      className="group flex items-start gap-3 rounded-xl border border-transparent p-3 transition-colors duration-swift hover:border-glass-border/60 hover:bg-card/50"
      data-testid="estate-metric"
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-3.5 w-3.5" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
          {label}
        </p>
        <p className="mt-1 text-2xl font-semibold tabular-nums leading-none">
          {value}
        </p>
        <p className="mt-1 text-[0.7rem] leading-5 text-muted-foreground">
          {detail}
        </p>
      </div>
    </div>
  );
}

function SectionShell({
  testId,
  title,
  detail,
  children,
}: {
  testId: string;
  title: string;
  detail: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className="instrument-panel overflow-hidden rounded-2xl"
      data-testid={testId}
    >
      <div className="border-b border-glass-border/50 px-4 py-3">
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">{detail}</p>
      </div>
      {children}
    </section>
  );
}

function EmptyRow({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-4 py-5 text-xs text-muted-foreground">{children}</div>
  );
}

export function EstateOverview({ health }: { health: EstateHealth }) {
  const summary = health.summary;

  return (
    <section className="flex flex-col gap-5" data-testid="estate-overview">
      <header className="glass-deep rounded-3xl p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[0.62rem] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Estate overview
            </p>
            <h1 className="mt-2 text-[1.8rem] font-semibold leading-tight tracking-tight sm:text-3xl">
              Agent control plane
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
              Fleet health, pending work, and risk signals for this workspace.
              Every claim below carries its source.
            </p>
          </div>
          <span
            className={cn(
              "status-chip",
              sourceChipClass(health.data_source),
            )}
            data-testid="estate-data-source"
            title={health.degraded_reason ?? health.provenance.join(", ")}
          >
            <span className="status-chip__dot" />
            {SOURCE_LABEL[health.data_source]}
          </span>
        </div>
        {health.degraded_reason ? (
          <div
            className="notice notice--warning mt-4"
            data-testid="estate-degraded-reason"
          >
            <AlertTriangle className="notice__icon h-3.5 w-3.5" aria-hidden />
            <div className="notice__body">{health.degraded_reason}</div>
          </div>
        ) : null}

        {/* Metric strip — six numbers in one row, not six cards. */}
        <div
          className="mt-6 grid grid-cols-2 gap-1 sm:grid-cols-3 xl:grid-cols-6"
          aria-label="Estate metrics"
        >
          <MetricCell
            label="Agents"
            value={summary.agents_total}
            detail={`${summary.agents_production} prod, ${summary.agents_draft} draft`}
            icon={Bot}
          />
          <MetricCell
            label="Blocked"
            value={summary.blocked_deploys + summary.pending_approvals}
            detail={`${summary.pending_approvals} approvals, ${summary.blocked_deploys} deploys`}
            icon={GitPullRequestArrow}
          />
          <MetricCell
            label="Rollouts"
            value={summary.active_rollouts}
            detail="Shadow / canary / ramp"
            icon={Rocket}
          />
          <MetricCell
            label="Handoffs"
            value={summary.pending_handoffs}
            detail="Open HITL queue"
            icon={Inbox}
          />
          <MetricCell
            label="Evidence"
            value={summary.trace_count + summary.eval_suites}
            detail={`${summary.trace_errors} errors, ${summary.eval_suites} suites`}
            icon={TestTube2}
          />
          <MetricCell
            label="Catches"
            value={summary.open_catches}
            detail="Adversarial pending"
            icon={AlertTriangle}
          />
        </div>
      </header>

      {/* Needs attention — the primary feed. */}
      <section
        className="instrument-panel overflow-hidden rounded-2xl"
        data-testid="estate-attention"
      >
        <div className="flex items-center justify-between gap-3 border-b border-glass-border/50 px-4 py-3">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-3.5 w-3.5 text-primary" aria-hidden />
            <h2 className="text-sm font-semibold">Needs attention</h2>
          </div>
          <p className="text-[0.7rem] text-muted-foreground">
            Sorted by operational risk
          </p>
        </div>
        {health.attention.length > 0 ? (
          <ol className="divide-y divide-glass-border/40">
            {health.attention.map((item) => {
              const Icon = severityIcon(item.severity);
              return (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    className="group flex items-start gap-3 px-4 py-3 transition-colors hover:bg-muted/40"
                  >
                    <span
                      className={cn(
                        "mt-0.5 inline-flex h-6 items-center gap-1.5 rounded-full px-2 text-[0.65rem] font-semibold",
                        severityChip(item.severity).replace(
                          "status-chip--",
                          "",
                        ) === "warning"
                          ? "border border-warning/40 bg-warning/10 text-warning"
                          : severityChip(item.severity).replace(
                                "status-chip--",
                                "",
                              ) === "info"
                            ? "border border-info/40 bg-info/10 text-info"
                            : "border border-success/40 bg-success/10 text-success",
                      )}
                    >
                      <Icon className="h-3 w-3" aria-hidden />
                      {item.severity}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold leading-tight">
                        {item.title}
                      </span>
                      <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                        {item.detail}
                      </span>
                      <span className="mt-1.5 block font-mono text-[0.65rem] text-muted-foreground/80">
                        source: {item.source}
                      </span>
                    </span>
                    <ArrowRight
                      className="mt-1 h-3.5 w-3.5 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground"
                      aria-hidden
                    />
                  </Link>
                </li>
              );
            })}
          </ol>
        ) : (
          <EmptyRow>No estate-level work requires attention.</EmptyRow>
        )}
      </section>

      {/* Two-column operational + risk grid. */}
      <div className="grid gap-4 xl:grid-cols-2">
        <SectionShell
          testId="estate-rollouts"
          title="Rollout posture"
          detail="Shadow, canary, ramp, pause, rollback state across agents."
        >
          {health.rollout_health.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.rollout_health.map((item) => (
                <li key={item.id}>
                  <Link
                    href={`/agents/${item.agent_id}/deploys?deployment_id=${item.id}`}
                    className="group block px-4 py-3 transition-colors hover:bg-muted/40"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">
                        {item.agent_name}
                        <span className="ml-1.5 font-mono text-xs font-normal text-muted-foreground">
                          {item.version_id}
                        </span>
                      </p>
                      <span
                        className={cn(
                          "status-chip",
                          item.status === "paused" ||
                            item.status === "rolled_back" ||
                            item.status === "failed"
                            ? "status-chip--warning"
                            : "status-chip--info",
                        )}
                      >
                        {item.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.stage} · {item.traffic_percent}% · hold{" "}
                      {item.hold_time_minutes}m
                    </p>
                    <p className="mt-1 text-[0.7rem] text-muted-foreground/90">
                      {item.channel_scope.length
                        ? item.channel_scope.join(", ")
                        : "channels: not scoped"}
                      {item.region_scope.length
                        ? ` · ${item.region_scope.join(", ")}`
                        : ""}
                      {item.segment_scope.length
                        ? ` · ${item.segment_scope.join(", ")}`
                        : ""}
                    </p>
                    <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground/80">
                      {item.evidence_ref}
                    </p>
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No active rollout state detected.</EmptyRow>
          )}
        </SectionShell>

        <SectionShell
          testId="estate-shared-dependencies"
          title="Shared dependency risk"
          detail="Cross-agent tools and dependencies with fleet-wide blast radius."
        >
          {health.shared_dependencies.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.shared_dependencies.map((item) => (
                <li key={item.id} className="px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold">{item.name}</p>
                    <span
                      className={cn(
                        "status-chip",
                        severityChip(severityRisk(item.risk)),
                      )}
                    >
                      {item.risk}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.detail}
                  </p>
                  <p className="mt-1 truncate text-[0.7rem] text-muted-foreground/80">
                    {item.agents
                      .map((agent) => agent.agent_name)
                      .slice(0, 3)
                      .join(", ")}
                    {item.agents.length > 3 ? ` +${item.agents.length - 3}` : ""}
                  </p>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No shared dependency risk detected.</EmptyRow>
          )}
        </SectionShell>

        <SectionShell
          testId="estate-failure-clusters"
          title="Cross-agent failures"
          detail="Clusters, incidents, and trace errors that can become evals."
        >
          {health.failure_clusters.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.failure_clusters.map((item) => (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    className="group block px-4 py-3 transition-colors hover:bg-muted/40"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">{item.title}</p>
                      <span
                        className={cn(
                          "status-chip",
                          severityChip(severityRisk(item.severity)),
                        )}
                      >
                        {item.severity}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.affected} affected conversation
                      {item.affected === 1 ? "" : "s"}
                    </p>
                    <p className="mt-1 font-mono text-[0.65rem] text-muted-foreground/80">
                      {item.evidence_ref}
                    </p>
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No cross-agent failure clusters detected.</EmptyRow>
          )}
        </SectionShell>

        <SectionShell
          testId="estate-channels"
          title="Channel health"
          detail="Channel readiness across the fleet, not just voice."
        >
          {health.channel_health.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.channel_health.map((item) => (
                <li
                  key={item.id}
                  className="flex items-start justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">
                      {item.agent_name}{" "}
                      <span className="font-normal text-muted-foreground">
                        · {item.channel_type.replace(/_/g, " ")}
                      </span>
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {item.blocking_checks} readiness blocker
                      {item.blocking_checks === 1 ? "" : "s"}
                    </p>
                  </div>
                  <span className="status-chip status-chip--neutral">
                    {item.status}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No configured channel blockers detected.</EmptyRow>
          )}
        </SectionShell>

        <SectionShell
          testId="estate-continuity"
          title="Continuity risks"
          detail="Owner and backup-owner gaps that affect handoff and incidents."
        >
          {health.owner_risks.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.owner_risks.map((item) => (
                <li key={item.id}>
                  <Link
                    href={item.href}
                    className="group block px-4 py-3 transition-colors hover:bg-muted/40"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">{item.agent_name}</p>
                      <span
                        className={cn(
                          "status-chip",
                          severityChip(
                            item.severity === "critical" ? "critical" : "watch",
                          ),
                        )}
                      >
                        {item.severity}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.detail}
                    </p>
                    <p className="mt-1 text-[0.7rem] text-muted-foreground/80">
                      Owner: {item.owner_user_id || "unassigned"} · Backup:{" "}
                      {item.backup_owner_user_id || "unassigned"}
                    </p>
                  </Link>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No ownership continuity gaps detected.</EmptyRow>
          )}
        </SectionShell>

        <SectionShell
          testId="estate-jobs"
          title="Background analysis jobs"
          detail="Drift, failure, cost, latency, knowledge, and handoff detectors."
        >
          {health.background_jobs.length ? (
            <ol className="divide-y divide-glass-border/40">
              {health.background_jobs.map((job) => (
                <li
                  key={job.id}
                  className="flex items-start justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">
                      {job.id.replace(/_/g, " ")}
                    </p>
                    <p className="mt-0.5 font-mono text-[0.65rem] text-muted-foreground/80">
                      {job.evidence_ref}
                    </p>
                  </div>
                  <span className="status-chip status-chip--neutral">
                    {job.status} · {job.output_count}
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyRow>No estate analysis jobs have run yet.</EmptyRow>
          )}
        </SectionShell>
      </div>
    </section>
  );
}

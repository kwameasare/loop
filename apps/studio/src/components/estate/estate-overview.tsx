import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Bot,
  ClipboardCheck,
  GitPullRequestArrow,
  Inbox,
  RadioTower,
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

function sourceTone(source: EstateHealthDataSource): string {
  if (source === "live") return "border-success/40 bg-success/10 text-success";
  if (source === "derived") return "border-info/40 bg-info/10 text-info";
  return "border-warning/50 bg-warning/10 text-warning";
}

function severityIcon(severity: EstateAttentionItem["severity"]): LucideIcon {
  if (severity === "critical") return AlertTriangle;
  if (severity === "watch") return RadioTower;
  return ShieldCheck;
}

function severityClass(severity: EstateAttentionItem["severity"]): string {
  if (severity === "critical") return "bg-warning/10 text-warning";
  if (severity === "watch") return "bg-info/10 text-info";
  return "bg-success/10 text-success";
}

function Metric({
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
    <div className="rounded-md border bg-card p-4" data-testid="estate-metric">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
        </div>
        <span className="grid h-8 w-8 place-items-center rounded-md bg-muted text-muted-foreground">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

export function EstateOverview({ health }: { health: EstateHealth }) {
  const summary = health.summary;
  return (
    <section className="flex flex-col gap-4" data-testid="estate-overview">
      <header className="rounded-md border bg-card p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Estate overview
            </p>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight">
              Agent control plane
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              Fleet health, pending work, and risk signals for this workspace.
              Every operational claim below includes a source.
            </p>
          </div>
          <div
            className={cn(
              "inline-flex w-fit items-center gap-2 rounded-md border px-2.5 py-1.5 text-xs font-medium",
              sourceTone(health.data_source),
            )}
            data-testid="estate-data-source"
            title={health.degraded_reason ?? health.provenance.join(", ")}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {SOURCE_LABEL[health.data_source]}
          </div>
        </div>
        {health.degraded_reason ? (
          <p
            className="mt-3 rounded-md border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning"
            data-testid="estate-degraded-reason"
          >
            {health.degraded_reason}
          </p>
        ) : null}
      </header>

      <div
        className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"
        aria-label="Estate metrics"
      >
        <Metric
          label="Agents"
          value={summary.agents_total}
          detail={`${summary.agents_production} production, ${summary.agents_draft} draft`}
          icon={Bot}
        />
        <Metric
          label="Blocked work"
          value={summary.blocked_deploys + summary.pending_approvals}
          detail={`${summary.pending_approvals} approval(s), ${summary.blocked_deploys} deploy block(s)`}
          icon={GitPullRequestArrow}
        />
        <Metric
          label="Human handoffs"
          value={summary.pending_handoffs}
          detail="Open HITL queue items"
          icon={Inbox}
        />
        <Metric
          label="Evidence"
          value={summary.trace_count + summary.eval_suites}
          detail={`${summary.trace_errors} trace error(s), ${summary.eval_suites} eval suite(s)`}
          icon={TestTube2}
        />
      </div>

      <div className="rounded-md border bg-card" data-testid="estate-attention">
        <div className="border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <ClipboardCheck className="h-4 w-4 text-primary" aria-hidden />
            <h2 className="text-base font-semibold">Needs attention</h2>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Sorted by operational risk. Items are hidden until the backing
            object exists.
          </p>
        </div>
        {health.attention.length > 0 ? (
          <ol className="divide-y">
            {health.attention.map((item) => {
              const Icon = severityIcon(item.severity);
              return (
                <li key={item.id} className="p-4">
                  <Link
                    href={item.href}
                    className="group flex items-start gap-3 rounded-md p-1 -m-1 transition-colors hover:bg-muted/60"
                  >
                    <span
                      className={cn(
                        "mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-md border",
                        severityClass(item.severity),
                      )}
                    >
                      <Icon className="h-4 w-4" aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold">
                        {item.title}
                      </span>
                      <span className="mt-1 block text-sm text-muted-foreground">
                        {item.detail}
                      </span>
                      <span className="mt-2 block font-mono text-xs text-muted-foreground">
                        source: {item.source}
                      </span>
                    </span>
                    <span className="hidden shrink-0 items-center gap-1 text-xs font-medium text-muted-foreground group-hover:text-foreground sm:inline-flex">
                      Open
                      <ArrowRight className="h-3.5 w-3.5" />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ol>
        ) : (
          <div className="p-4 text-sm text-muted-foreground">
            No estate-level work requires attention.
          </div>
        )}
      </div>
    </section>
  );
}

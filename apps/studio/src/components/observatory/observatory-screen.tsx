"use client";

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Eye,
  Pause,
  Play,
  Radio,
  Route,
} from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
} from "@/components/target";
import {
  createIncidentFixChangePackage,
  seedIncidentEvalCases,
  transitionIncident,
} from "@/lib/incidents";
import {
  createObservatoryAnomalyEvalCase,
  createObservatoryAnomalyTask,
  pinObservatoryMetric,
} from "@/lib/observatory";
import type { IncidentRecord } from "@/lib/incidents";
import type {
  AmbientAgentHealth,
  ObservatoryAnomaly,
  ObservatoryMetric,
  ObservatoryModel,
  ObservatoryTone,
  ProductionTailEvent,
} from "@/lib/observatory";
import { cn } from "@/lib/utils";

const TONE_CLASS: Record<ObservatoryTone, string> = {
  healthy: "border-success/40 bg-success/10 text-success",
  watching: "border-info/40 bg-info/10 text-info",
  drifting: "border-warning/40 bg-warning/10 text-warning",
  blocked: "border-destructive/40 bg-destructive/10 text-destructive",
};

const SEVERITY_TONE: Record<ObservatoryAnomaly["severity"], string> = {
  low: "border-info/40 bg-info/10 text-info",
  medium: "border-warning/40 bg-warning/10 text-warning",
  high: "border-destructive/40 bg-destructive/10 text-destructive",
  critical: "border-destructive bg-destructive text-destructive-foreground",
};

function tracesHref(traceQuery: string, agentId?: string): string {
  const params = new URLSearchParams();
  if (agentId) params.set("agent_id", agentId);
  if (traceQuery === "status:error") {
    params.set("only_errors", "true");
  } else if (traceQuery) {
    params.set("filter", traceQuery);
  }
  const qs = params.toString();
  return `/traces${qs ? `?${qs}` : ""}`;
}

function reportText(
  report: Record<string, unknown>,
  key: string,
  fallback = "Not recorded",
): string {
  const value = report[key];
  return typeof value === "string" && value.trim() ? value : fallback;
}

function reportList(
  report: Record<string, unknown>,
  key: string,
  fallback: readonly string[] = [],
): string[] {
  const value = report[key];
  if (!Array.isArray(value)) return [...fallback];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function reportTimeline(incident: IncidentRecord) {
  const value = incident.report.timeline;
  if (!Array.isArray(value)) return incident.timeline;
  return value
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      return {
        kind: typeof row.kind === "string" ? row.kind : "event",
        at: typeof row.at === "string" ? row.at : "",
        summary:
          typeof row.summary === "string" ? row.summary : "Incident event.",
      };
    })
    .filter((item): item is { kind: string; at: string; summary: string } =>
      Boolean(item),
    );
}

function editHrefForAffectedObject(
  anomaly: ObservatoryAnomaly,
  agentId?: string,
): { href: string; label: string } | null {
  if (anomaly.editSurface === "inbox") {
    return {
      href: agentId ? `/inbox?agent_id=${agentId}` : "/inbox",
      label: "Open inbox",
    };
  }
  if (anomaly.editSurface === "incidents") {
    const params = new URLSearchParams();
    if (agentId) params.set("agent_id", agentId);
    params.set("incident_id", anomaly.id.replace(/^incident_/, ""));
    return {
      href: `/observe?${params.toString()}`,
      label: "Open incident",
    };
  }
  if (anomaly.editSurface === "observe") {
    return { href: "/observe", label: "Open observatory" };
  }
  if (!agentId) return null;
  if (anomaly.editSurface === "behavior") {
    return { href: `/agents/${agentId}/behavior`, label: "Open behavior" };
  }
  if (anomaly.editSurface === "knowledge") {
    return { href: `/agents/${agentId}/kb`, label: "Open knowledge" };
  }
  if (anomaly.editSurface === "tools") {
    return { href: `/agents/${agentId}/tools`, label: "Open tools" };
  }
  if (anomaly.editSurface === "memory") {
    return { href: `/agents/${agentId}/memory`, label: "Open memory" };
  }
  if (anomaly.editSurface === "channels") {
    return { href: `/agents/${agentId}/channels`, label: "Open channels" };
  }
  if (anomaly.editSurface === "traces") {
    return { href: `/agents/${agentId}/traces`, label: "Inspect spans" };
  }
  const target = anomaly.affectedObject.toLowerCase();
  if (target.startsWith("behavior/")) {
    return { href: `/agents/${agentId}/behavior`, label: "Open behavior" };
  }
  if (target.startsWith("knowledge/")) {
    return { href: `/agents/${agentId}/kb`, label: "Open knowledge" };
  }
  if (target.startsWith("tool/")) {
    return { href: `/agents/${agentId}/tools`, label: "Open tools" };
  }
  if (target.startsWith("memory/")) {
    return { href: `/agents/${agentId}/memory`, label: "Open memory" };
  }
  if (target.startsWith("channel/")) {
    return { href: `/agents/${agentId}/channels`, label: "Open channels" };
  }
  if (target.includes("latency")) {
    return { href: `/agents/${agentId}/traces`, label: "Inspect spans" };
  }
  if (target.includes("operator inbox")) {
    return { href: `/inbox?agent_id=${agentId}`, label: "Open inbox" };
  }
  return { href: `/agents/${agentId}/observe`, label: "Open observatory" };
}

function MetricCard({
  metric,
  onPin,
  pinned,
  pending,
}: {
  metric: ObservatoryMetric;
  onPin?: () => void;
  pinned?: boolean;
  pending?: boolean;
}) {
  return (
    <article
      className="rounded-md border bg-card p-4"
      data-testid={`observatory-metric-${metric.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase text-muted-foreground">
          {metric.label}
        </p>
        <span
          className={cn(
            "rounded-md border px-2 py-0.5 text-xs",
            TONE_CLASS[metric.tone],
          )}
        >
          {metric.tone}
        </span>
      </div>
      <p className="mt-3 text-2xl font-semibold tabular-nums">{metric.value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{metric.delta}</p>
      <p className="mt-3 text-sm">{metric.nextAction}</p>
      {onPin ? (
        <Button
          type="button"
          variant={pinned ? "subtle" : "outline"}
          size="sm"
          className="mt-3"
          onClick={onPin}
          disabled={pending || pinned}
          data-testid={`observatory-pin-${metric.id}`}
        >
          {pending ? "Pinning" : pinned ? "Pinned" : "Pin chart to dashboard"}
        </Button>
      ) : null}
    </article>
  );
}

function AnomalyCard({
  anomaly,
  acknowledged,
  workspaceId,
  agentId,
  onAcknowledge,
}: {
  anomaly: ObservatoryAnomaly;
  acknowledged: boolean;
  workspaceId?: string | undefined;
  agentId?: string | undefined;
  onAcknowledge: () => void;
}) {
  const [taskRef, setTaskRef] = useState(anomaly.taskRef ?? null);
  const [evalRef, setEvalRef] = useState(anomaly.evalCandidateRef ?? null);
  const [busy, setBusy] = useState<"task" | "eval" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const editLink = editHrefForAffectedObject(anomaly, agentId);

  async function createTask() {
    if (!workspaceId || taskRef) return;
    setBusy("task");
    setError(null);
    try {
      const ref = await createObservatoryAnomalyTask(workspaceId, anomaly);
      setTaskRef(ref.id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not create anomaly task.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function createEval() {
    if (!workspaceId || evalRef) return;
    setBusy("eval");
    setError(null);
    try {
      const ref = await createObservatoryAnomalyEvalCase(workspaceId, anomaly);
      setEvalRef(ref.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create anomaly eval case.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="rounded-md border bg-card p-4">
      <div className="flex items-start gap-3">
        <AlertTriangle
          className="mt-0.5 h-5 w-5 text-warning"
          aria-hidden={true}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <h3 className="text-sm font-semibold">{anomaly.title}</h3>
            <span
              className={cn(
                "rounded-md border px-2 py-0.5 text-xs",
                SEVERITY_TONE[anomaly.severity],
              )}
            >
              {anomaly.severity}
            </span>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {anomaly.evidence}
          </p>
          <dl className="mt-3 grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
            <div>
              <dt className="font-semibold uppercase tracking-wide">
                Affected object
              </dt>
              <dd className="mt-1 break-all">{anomaly.affectedObject}</dd>
            </div>
            <div>
              <dt className="font-semibold uppercase tracking-wide">
                Trace query
              </dt>
              <dd className="mt-1 break-all">{anomaly.traceQuery}</dd>
            </div>
          </dl>
          <div
            className="mt-3 grid gap-3 rounded-md border bg-background/60 p-3 text-xs sm:grid-cols-2"
            data-testid={`anomaly-commitment-delta-${anomaly.id}`}
          >
            <div>
              <p className="font-semibold uppercase tracking-wide text-muted-foreground">
                Observed
              </p>
              <p className="mt-1 text-foreground">{anomaly.observedBehavior}</p>
            </div>
            <div>
              <p className="font-semibold uppercase tracking-wide text-muted-foreground">
                Intended
              </p>
              <p className="mt-1 text-foreground">{anomaly.intendedBehavior}</p>
            </div>
          </div>
          <p className="mt-3 text-sm">{anomaly.nextAction}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Owner: {anomaly.owner}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              className={buttonVariants({ variant: "outline", size: "sm" })}
              href={tracesHref(anomaly.traceQuery, agentId)}
              data-testid={`anomaly-open-traces-${anomaly.id}`}
            >
              Open traces
            </a>
            {editLink ? (
              <a
                className={buttonVariants({ variant: "outline", size: "sm" })}
                href={editLink.href}
                data-testid={`anomaly-open-edit-${anomaly.id}`}
              >
                {editLink.label}
              </a>
            ) : null}
            <Button
              type="button"
              variant={acknowledged ? "subtle" : "outline"}
              size="sm"
              onClick={onAcknowledge}
            >
              {acknowledged ? "Acknowledged" : "Acknowledge with evidence"}
            </Button>
            {workspaceId ? (
              <>
                <Button
                  type="button"
                  variant={taskRef ? "subtle" : "outline"}
                  size="sm"
                  disabled={busy === "task" || Boolean(taskRef)}
                  onClick={() => void createTask()}
                  data-testid={`anomaly-task-${anomaly.id}`}
                >
                  {busy === "task"
                    ? "Creating task"
                    : taskRef
                      ? "Task created"
                      : "Create task"}
                </Button>
                <Button
                  type="button"
                  variant={evalRef ? "subtle" : "outline"}
                  size="sm"
                  disabled={busy === "eval" || Boolean(evalRef)}
                  onClick={() => void createEval()}
                  data-testid={`anomaly-eval-${anomaly.id}`}
                >
                  {busy === "eval"
                    ? "Saving eval"
                    : evalRef
                      ? "Eval seeded"
                      : "Seed eval"}
                </Button>
              </>
            ) : null}
          </div>
          {taskRef || evalRef ? (
            <p
              className="mt-2 text-xs text-muted-foreground"
              data-testid={`anomaly-action-refs-${anomaly.id}`}
            >
              {taskRef ? `Task: ${taskRef}` : null}
              {taskRef && evalRef ? " · " : null}
              {evalRef ? `Eval: ${evalRef}` : null}
            </p>
          ) : null}
          {error ? (
            <p
              className="mt-2 rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive"
              role="alert"
            >
              {error}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function AgentHealthArc({ agent }: { agent: AmbientAgentHealth }) {
  return (
    <article
      className="rounded-md border bg-card p-4"
      data-testid={`ambient-health-${agent.id}`}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "relative h-14 w-14 rounded-full border-4 bg-background",
            agent.tone === "healthy"
              ? "border-success"
              : agent.tone === "watching"
                ? "border-info"
                : agent.tone === "drifting"
                  ? "border-warning"
                  : "border-destructive",
          )}
          aria-label={`${agent.name} ambient health ${agent.tone}`}
        >
          <div className="absolute inset-2 rounded-full bg-muted/50" />
          <Radio className="absolute left-1/2 top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 text-muted-foreground" />
        </div>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold">{agent.name}</h3>
          <p className="text-xs text-muted-foreground">
            {agent.evalPassRate}% eval - {agent.p95LatencyMs} ms p95 -{" "}
            {agent.escalationRate}% escalation
          </p>
        </div>
      </div>
      <ConfidenceMeter
        className="mt-4"
        value={agent.evalPassRate}
        label="Eval health"
        evidence={`${agent.costDeltaPct}% cost delta against baseline`}
      />
    </article>
  );
}

function TailRow({ event }: { event: ProductionTailEvent }) {
  return (
    <article className="border-b px-3 py-3 text-sm last:border-b-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">
            {event.time}
          </span>
          <span className="rounded-md border bg-background px-2 py-0.5 text-xs">
            {event.channel}
          </span>
        </div>
        <span className="flex items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">
            {event.traceId}
          </span>
          <span
            className={cn(
              "h-2.5 w-2.5 rounded-full",
              event.status === "healthy"
                ? "bg-success"
                : event.status === "watching"
                  ? "bg-info"
                  : "bg-warning",
            )}
          />
        </span>
      </div>
      <p className="mt-2 text-muted-foreground">{event.summary}</p>
      <a
        className={cn(
          buttonVariants({ variant: "ghost", size: "sm" }),
          "mt-2 px-0 text-xs text-info hover:bg-transparent",
        )}
        href={`/traces/${encodeURIComponent(event.traceId)}`}
        data-testid={`tail-open-trace-${event.id}`}
      >
        Open trace <ArrowRight className="ml-1 h-3.5 w-3.5" />
      </a>
    </article>
  );
}

function IncidentResponsePanel({
  incidents,
  focusedIncidentId,
  focusIncidents,
}: {
  incidents: readonly IncidentRecord[];
  focusedIncidentId?: string | undefined;
  focusIncidents?: boolean | undefined;
}) {
  const [seeded, setSeeded] = useState<Record<string, string>>({});
  const [fixPackages, setFixPackages] = useState<Record<string, string>>({});
  const [incidentStates, setIncidentStates] = useState<
    Record<string, IncidentRecord>
  >({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function seedIncident(incident: IncidentRecord) {
    setBusy(incident.id);
    setError(null);
    try {
      const response = await seedIncidentEvalCases(
        incident.agent_id,
        incident.id,
      );
      setSeeded((current) => ({
        ...current,
        [incident.id]: response.suite_id,
      }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not seed incident eval cases.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function createFixPackage(incident: IncidentRecord) {
    setBusy(`fix:${incident.id}`);
    setError(null);
    try {
      const response = await createIncidentFixChangePackage(
        incident.agent_id,
        incident.id,
      );
      setFixPackages((current) => ({
        ...current,
        [incident.id]: response.change_package.id,
      }));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not create incident fix package.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function moveIncident(
    incident: IncidentRecord,
    action: "investigate" | "resolve" | "archive",
  ) {
    setBusy(`${action}:${incident.id}`);
    setError(null);
    try {
      const response = await transitionIncident(
        incident.agent_id,
        incident.id,
        action,
        action === "investigate"
          ? "Operator is investigating root cause."
          : action === "resolve"
            ? "Fix package and regression evidence reviewed."
            : "Postmortem evidence archived.",
      );
      setIncidentStates((current) => ({
        ...current,
        [incident.id]: response,
      }));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not update incident state.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      className={cn(
        "space-y-3 rounded-md",
        focusIncidents
          ? "ring-2 ring-focus ring-offset-4 ring-offset-background"
          : "",
      )}
      data-testid="observatory-incidents"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" aria-hidden={true} />
          <h2 className="text-lg font-semibold">Incident response</h2>
        </div>
        <LiveBadge tone={incidents.length > 0 ? "paused" : "live"}>
          {incidents.length > 0 ? `${incidents.length} active` : "clear"}
        </LiveBadge>
      </div>

      {focusIncidents ? (
        <p
          className="rounded-md border border-info/40 bg-info/5 px-3 py-2 text-sm text-info"
          data-testid="observatory-focused-incidents"
        >
          Opened from Workbench evidence. Review active incidents, containment,
          rollback refs, seeded evals, and fix Change Packages for this agent.
        </p>
      ) : null}

      {error ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}

      {incidents.length === 0 ? (
        <article className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
          No active incidents. Rollback, pause, anomaly, and seeded eval records
          will appear here when production needs containment.
        </article>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {incidents.map((rawIncident) => {
            const incident = incidentStates[rawIncident.id] ?? rawIncident;
            const seededSuite =
              seeded[incident.id] ?? incident.candidate_eval_suite_id;
            const fixPackage =
              fixPackages[incident.id] ?? incident.fix_change_package_id;
            const isClosed =
              incident.status === "resolved" || incident.status === "archived";
            const reportChannels = reportList(
              incident.report,
              "affected_channels",
              incident.channel_scope,
            );
            const reportActions = reportList(
              incident.report,
              "actions_taken",
              incident.rollback_action_ref ? [incident.rollback_action_ref] : [],
            );
            const candidateTests = reportList(
              incident.report,
              "candidate_regression_tests",
              incident.affected_trace_ids,
            );
            const timeline = reportTimeline(incident);
            return (
              <article
                key={incident.id}
                className={cn(
                  "rounded-md border bg-card p-4",
                  incident.id === focusedIncidentId
                    ? "ring-2 ring-focus ring-offset-2 ring-offset-background"
                    : "",
                )}
                data-testid={`incident-card-${incident.id}`}
                data-focused={
                  incident.id === focusedIncidentId ? "true" : "false"
                }
              >
                {incident.id === focusedIncidentId ? (
                  <p
                    className="mb-3 rounded-md border border-info/40 bg-info/5 px-3 py-2 text-xs text-info"
                    data-testid={`incident-focused-${incident.id}`}
                  >
                    Opened from evidence link: incident {incident.id} is
                    focused.
                  </p>
                ) : null}
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase text-muted-foreground">
                      {incident.severity} incident
                    </p>
                    <h3 className="mt-1 text-sm font-semibold">
                      {incident.trigger}
                    </h3>
                  </div>
                  <span
                    className={cn(
                      "rounded-md border px-2 py-0.5 text-xs",
                      incident.status === "contained"
                        ? "border-info/40 bg-info/10 text-info"
                        : incident.status === "resolved"
                          ? "border-success/40 bg-success/10 text-success"
                          : "border-warning/40 bg-warning/10 text-warning",
                    )}
                  >
                    {incident.status}
                  </span>
                </div>
                <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-muted-foreground">Affected</dt>
                    <dd>
                      {incident.affected_conversation_count} conversations ·{" "}
                      {incident.affected_trace_ids.length} traces
                    </dd>
                  </div>
                  <div>
                    <dt className="text-muted-foreground">Rollback</dt>
                    <dd className="break-all">
                      {incident.rollback_action_ref || "not executed"}
                    </dd>
                  </div>
                </dl>
                <p className="mt-3 text-sm text-muted-foreground">
                  {incident.root_cause_hypothesis}
                </p>
                <p className="mt-2 text-sm">{incident.proposed_fix}</p>
                <div
                  className="mt-3 rounded-md border bg-background/60 p-3"
                  data-testid={`incident-report-${incident.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase text-muted-foreground">
                      Generated incident report
                    </p>
                    <span className="rounded-md border px-2 py-0.5 text-xs text-muted-foreground">
                      rollback {reportText(incident.report, "rollback_status")}
                    </span>
                  </div>
                  <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                    <div>
                      <dt className="text-muted-foreground">Customer impact</dt>
                      <dd>{reportText(incident.report, "customer_impact")}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Channels</dt>
                      <dd>
                        {reportChannels.length > 0
                          ? reportChannels.join(", ")
                          : "All channels"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Actions taken</dt>
                      <dd className="break-all">
                        {reportActions.length > 0
                          ? reportActions.join(", ")
                          : "None yet"}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">
                        Candidate regressions
                      </dt>
                      <dd>
                        {candidateTests.length > 0
                          ? `${candidateTests.length} trace-backed test(s)`
                          : "Seed from affected traces"}
                      </dd>
                    </div>
                  </dl>
                  {timeline.length > 0 ? (
                    <ol className="mt-3 space-y-2 text-xs">
                      {timeline.slice(0, 4).map((event, index) => (
                        <li
                          key={`${event.kind}-${event.at}-${index}`}
                          className="grid gap-2 rounded-md border bg-card px-2 py-1.5 sm:grid-cols-[7rem_minmax(0,1fr)]"
                        >
                          <span className="font-mono text-muted-foreground">
                            {event.kind}
                          </span>
                          <span>{event.summary}</span>
                        </li>
                      ))}
                    </ol>
                  ) : null}
                </div>
                {incident.notifications.length > 0 ? (
                  <div
                    className="mt-3 rounded-md border border-info/30 bg-info/5 p-3 text-xs"
                    data-testid={`incident-notifications-${incident.id}`}
                  >
                    <p className="font-semibold text-info">On-call notified</p>
                    <p className="mt-1 text-muted-foreground">
                      {incident.notifications
                        .map((notification) => notification.recipient)
                        .join(", ")}
                    </p>
                  </div>
                ) : null}
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant={seededSuite ? "subtle" : "outline"}
                    size="sm"
                    disabled={busy === incident.id}
                    onClick={() => void seedIncident(incident)}
                    data-testid={`incident-seed-${incident.id}`}
                  >
                    {busy === incident.id
                      ? "Seeding evals"
                      : seededSuite
                        ? "Eval suite seeded"
                        : "Seed incident evals"}
                  </Button>
                  {seededSuite ? (
                    <span
                      className="text-xs text-muted-foreground"
                      data-testid={`incident-suite-${incident.id}`}
                    >
                      {seededSuite}
                    </span>
                  ) : null}
                  <Button
                    type="button"
                    variant={fixPackage ? "subtle" : "outline"}
                    size="sm"
                    disabled={busy === `fix:${incident.id}`}
                    onClick={() => void createFixPackage(incident)}
                    data-testid={`incident-fix-package-${incident.id}`}
                  >
                    {busy === `fix:${incident.id}`
                      ? "Creating package"
                      : fixPackage
                        ? "Fix package staged"
                        : "Create fix package"}
                  </Button>
                  {fixPackage ? (
                    <span
                      className="text-xs text-muted-foreground"
                      data-testid={`incident-fix-package-id-${incident.id}`}
                    >
                      {fixPackage}
                    </span>
                  ) : null}
                  <Button
                    type="button"
                    variant={
                      incident.status === "investigating" ? "subtle" : "outline"
                    }
                    size="sm"
                    disabled={isClosed || busy === `investigate:${incident.id}`}
                    onClick={() => void moveIncident(incident, "investigate")}
                    data-testid={`incident-investigate-${incident.id}`}
                  >
                    {busy === `investigate:${incident.id}`
                      ? "Moving"
                      : incident.status === "investigating"
                        ? "Investigating"
                        : "Investigate"}
                  </Button>
                  <Button
                    type="button"
                    variant={
                      incident.status === "resolved" ? "subtle" : "outline"
                    }
                    size="sm"
                    disabled={isClosed || busy === `resolve:${incident.id}`}
                    onClick={() => void moveIncident(incident, "resolve")}
                    data-testid={`incident-resolve-${incident.id}`}
                  >
                    {busy === `resolve:${incident.id}`
                      ? "Resolving"
                      : "Resolve"}
                  </Button>
                  <Button
                    type="button"
                    variant={
                      incident.status === "archived" ? "subtle" : "outline"
                    }
                    size="sm"
                    disabled={
                      incident.status !== "resolved" ||
                      busy === `archive:${incident.id}`
                    }
                    onClick={() => void moveIncident(incident, "archive")}
                    data-testid={`incident-archive-${incident.id}`}
                  >
                    {busy === `archive:${incident.id}`
                      ? "Archiving"
                      : "Archive"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export function ObservatoryScreen({
  model,
  workspaceId,
  agentId,
  focusedIncidentId,
  focusIncidents = false,
}: {
  model: ObservatoryModel;
  workspaceId?: string;
  agentId?: string | undefined;
  focusedIncidentId?: string | undefined;
  focusIncidents?: boolean | undefined;
}) {
  const [paused, setPaused] = useState(false);
  const [acknowledged, setAcknowledged] = useState<string[]>([]);
  const [pinned, setPinned] = useState<string[]>([]);
  const [pinning, setPinning] = useState<string | null>(null);
  const [pinError, setPinError] = useState<string | null>(null);
  const degraded = Boolean(model.degradedReason);

  async function handlePin(metric: ObservatoryMetric) {
    if (!workspaceId || pinned.includes(metric.id)) return;
    setPinning(metric.id);
    setPinError(null);
    try {
      await pinObservatoryMetric(workspaceId, metric);
      setPinned((current) =>
        current.includes(metric.id) ? current : [...current, metric.id],
      );
    } catch (err) {
      setPinError(
        err instanceof Error ? err.message : "Could not pin dashboard metric.",
      );
    } finally {
      setPinning(null);
    }
  }

  return (
    <main
      className="mx-auto flex w-full max-w-7xl flex-col gap-8 p-6"
      data-testid="observatory-screen"
    >
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Observe / Observatory
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">
            Production posture at a glance
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Health, quality, latency, cost, knowledge, tools, channels, deploys,
            evals, anomalies, production tail, and ambient health arcs live in
            one operating surface.
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={() => setPaused((current) => !current)}
        >
          {paused ? (
            <Play className="mr-2 h-4 w-4" />
          ) : (
            <Pause className="mr-2 h-4 w-4" />
          )}
          {paused ? "Resume tail" : "Pause tail"}
        </Button>
      </header>

      {model.degradedReason ? (
        <section
          className="rounded-md border border-warning/40 bg-warning/10 p-4 text-sm text-warning"
          data-testid="observatory-degraded"
          role="status"
        >
          <p className="font-semibold">
            Live Observatory telemetry is unavailable.
          </p>
          <p className="mt-1">{model.degradedReason}</p>
        </section>
      ) : null}

      <section
        className="grid gap-3 md:grid-cols-2 xl:grid-cols-3"
        data-testid="observatory-dashboards"
      >
        {pinError ? (
          <p
            className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive md:col-span-2 xl:col-span-3"
            role="alert"
          >
            {pinError}
          </p>
        ) : null}
        {model.metrics.map((metric) => (
          <MetricCard
            key={metric.id}
            metric={metric}
            pinned={pinned.includes(metric.id)}
            pending={pinning === metric.id}
            {...(workspaceId
              ? {
                  onPin: () => void handlePin(metric),
                }
              : {})}
          />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.92fr_1.08fr]">
        <div className="space-y-3" data-testid="observatory-anomalies">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-info" aria-hidden={true} />
            <h2 className="text-lg font-semibold">Anomaly cards</h2>
          </div>
          {model.anomalies.map((anomaly) => (
            <AnomalyCard
              key={anomaly.id}
              anomaly={anomaly}
              acknowledged={acknowledged.includes(anomaly.id)}
              workspaceId={workspaceId}
              agentId={agentId}
              onAcknowledge={() =>
                setAcknowledged((current) =>
                  current.includes(anomaly.id)
                    ? current
                    : [...current, anomaly.id],
                )
              }
            />
          ))}
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Route className="h-5 w-5 text-info" aria-hidden={true} />
              <h2 className="text-lg font-semibold">Production tail</h2>
            </div>
            <LiveBadge tone={paused ? "paused" : "live"}>
              {degraded ? "offline" : paused ? "paused" : "streaming"}
            </LiveBadge>
          </div>
          <div
            className={cn(
              "overflow-hidden rounded-md border bg-card",
              paused && "opacity-70",
            )}
          >
            {model.tail.length > 0 ? (
              model.tail.map((event) => (
                <TailRow key={event.id} event={event} />
              ))
            ) : (
              <p className="p-4 text-sm text-muted-foreground">
                No production tail events loaded. Studio is not streaming
                placeholder turns.
              </p>
            )}
          </div>
          <EvidenceCallout
            title={model.recommendation.title}
            tone={model.recommendation.tone}
            confidence={model.recommendation.confidence}
            confidenceLevel={model.recommendation.confidenceLevel}
            source={model.recommendation.source}
          >
            <span className="block">{model.recommendation.body}</span>
            <span className="mt-2 block text-xs text-muted-foreground">
              Observed: {model.recommendation.observed}
            </span>
            <span className="mt-1 block text-xs text-muted-foreground">
              Intended: {model.recommendation.intended}
            </span>
          </EvidenceCallout>
        </div>
      </section>

      <IncidentResponsePanel
        incidents={model.incidents}
        focusedIncidentId={focusedIncidentId}
        focusIncidents={focusIncidents}
      />

      <section className="space-y-3" data-testid="ambient-health-arcs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-info" aria-hidden={true} />
            <h2 className="text-lg font-semibold">Ambient agent health</h2>
          </div>
          <LiveBadge tone={degraded ? "paused" : "live"}>
            {degraded ? "offline" : "peripheral signal"}
          </LiveBadge>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {model.agents.length > 0 ? (
            model.agents.map((agent) => (
              <AgentHealthArc key={agent.id} agent={agent} />
            ))
          ) : (
            <p className="rounded-md border bg-card p-4 text-sm text-muted-foreground lg:col-span-2">
              No agent health arcs loaded. The rail stays empty until live
              traces and cost records identify actual agents.
            </p>
          )}
        </div>
      </section>

      <section
        className="rounded-md border bg-card p-4"
        data-testid="observatory-second-monitor"
      >
        <div className="flex items-start gap-3">
          <BarChart3 className="mt-0.5 h-5 w-5 text-info" aria-hidden={true} />
          <div>
            <h2 className="text-sm font-semibold">Second monitor mode ready</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Tail, anomaly cards, and ambient arcs are designed to remain
              readable beside an editor without becoming a dashboard wall.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

"use client";

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Eye,
  Pause,
  Play,
  Radio,
  Route,
} from "lucide-react";

import { Button } from "@/components/ui/button";
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
import { pinObservatoryMetric } from "@/lib/observatory";
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
  onAcknowledge,
}: {
  anomaly: ObservatoryAnomaly;
  acknowledged: boolean;
  onAcknowledge: () => void;
}) {
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
          <p className="mt-3 text-sm">{anomaly.nextAction}</p>
          <p className="mt-2 text-xs text-muted-foreground">
            Owner: {anomaly.owner}
          </p>
          <Button
            type="button"
            variant={acknowledged ? "subtle" : "outline"}
            size="sm"
            className="mt-3"
            onClick={onAcknowledge}
          >
            {acknowledged ? "Acknowledged" : "Acknowledge with evidence"}
          </Button>
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
    </article>
  );
}

function IncidentResponsePanel({
  incidents,
}: {
  incidents: readonly IncidentRecord[];
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
        err instanceof Error
          ? err.message
          : "Could not update incident state.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-3" data-testid="observatory-incidents">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" aria-hidden={true} />
          <h2 className="text-lg font-semibold">Incident response</h2>
        </div>
        <LiveBadge tone={incidents.length > 0 ? "paused" : "live"}>
          {incidents.length > 0 ? `${incidents.length} active` : "clear"}
        </LiveBadge>
      </div>

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
            return (
              <article
                key={incident.id}
                className="rounded-md border bg-card p-4"
                data-testid={`incident-card-${incident.id}`}
              >
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
}: {
  model: ObservatoryModel;
  workspaceId?: string;
}) {
  const [paused, setPaused] = useState(false);
  const [acknowledged, setAcknowledged] = useState<string[]>([]);
  const [pinned, setPinned] = useState<string[]>([]);
  const [pinning, setPinning] = useState<string | null>(null);
  const [pinError, setPinError] = useState<string | null>(null);

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
              {paused ? "paused" : "streaming"}
            </LiveBadge>
          </div>
          <div
            className={cn(
              "overflow-hidden rounded-md border bg-card",
              paused && "opacity-70",
            )}
          >
            {model.tail.map((event) => (
              <TailRow key={event.id} event={event} />
            ))}
          </div>
          <EvidenceCallout
            title="Next best operating action"
            tone="warning"
            confidence={86}
            source="observatory/anomaly-ranking"
          >
            Fix the legal synonym cluster before raising canary above 25%. It is
            the only high-severity anomaly with production replay evidence and
            active deploy exposure.
          </EvidenceCallout>
        </div>
      </section>

      <IncidentResponsePanel incidents={model.incidents} />

      <section className="space-y-3" data-testid="ambient-health-arcs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Eye className="h-5 w-5 text-info" aria-hidden={true} />
            <h2 className="text-lg font-semibold">Ambient agent health</h2>
          </div>
          <LiveBadge tone="live">peripheral signal</LiveBadge>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {model.agents.map((agent) => (
            <AgentHealthArc key={agent.id} agent={agent} />
          ))}
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

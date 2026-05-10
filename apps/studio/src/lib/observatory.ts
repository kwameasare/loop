import {
  computeWorkspaceKpis,
  fetchUsageRecords,
  formatDeltaPercent,
  formatUSD,
  monthBoundsUTC,
  summariseCosts,
  type UsageClientOptions,
  type UsageRecord,
} from "@/lib/costs";
import {
  listInbox,
  type InboxClientOptions,
  type InboxItem,
} from "@/lib/inbox";
import { listWorkspaceIncidents, type IncidentRecord } from "@/lib/incidents";
import {
  searchTraces,
  type TraceSummary,
  type TracesClientOptions,
} from "@/lib/traces";
import { cpJson } from "@/lib/ux-wireup";

export type ObservatoryTone = "healthy" | "watching" | "drifting" | "blocked";

export interface ObservatoryMetric {
  id: string;
  label: string;
  value: string;
  delta: string;
  tone: ObservatoryTone;
  nextAction: string;
}

export interface ObservatoryAnomaly {
  id: string;
  title: string;
  severity: "low" | "medium" | "high" | "critical";
  evidence: string;
  affectedObject: string;
  observedBehavior: string;
  intendedBehavior: string;
  editSurface:
    | "behavior"
    | "knowledge"
    | "tools"
    | "memory"
    | "channels"
    | "traces"
    | "inbox"
    | "incidents"
    | "observe";
  nextAction: string;
  owner: string;
  traceQuery: string;
  taskRef?: string | undefined;
  evalCandidateRef?: string | undefined;
}

export interface ProductionTailEvent {
  id: string;
  time: string;
  channel: string;
  summary: string;
  traceId: string;
  status: ObservatoryTone;
}

export interface AmbientAgentHealth {
  id: string;
  name: string;
  evalPassRate: number;
  p95LatencyMs: number;
  costDeltaPct: number;
  escalationRate: number;
  tone: ObservatoryTone;
}

export interface ObservatoryRecommendation {
  title: string;
  body: string;
  observed: string;
  intended: string;
  source: string;
  confidence: number;
  confidenceLevel: "high" | "medium" | "low" | "unsupported";
  tone: "info" | "success" | "warning" | "danger";
}

export interface ObservatoryModel {
  metrics: readonly ObservatoryMetric[];
  anomalies: readonly ObservatoryAnomaly[];
  incidents: readonly IncidentRecord[];
  tail: readonly ProductionTailEvent[];
  agents: readonly AmbientAgentHealth[];
  recommendation: ObservatoryRecommendation;
  degradedReason?: string | undefined;
}

export interface ObservatoryDashboardLayout {
  id: string;
  name: string;
  layout: readonly { source_type: string; source_id: string; title: string }[];
  shared_with: readonly string[];
}

export interface ObservatoryActionRef {
  id: string;
  href?: string | undefined;
  evidence: string;
}

export interface ObservatoryClientOptions
  extends UsageClientOptions,
    TracesClientOptions,
    InboxClientOptions {}

type ObservatoryMutationOptions = ObservatoryClientOptions & {
  allowFixture?: boolean;
};

function hasCpApiBase(override?: string): boolean {
  return Boolean(
    override ??
      process.env.LOOP_CP_API_BASE_URL ??
      process.env.NEXT_PUBLIC_LOOP_API_URL,
  );
}

function toneFromScore(score: number): ObservatoryTone {
  if (score >= 95) return "healthy";
  if (score >= 85) return "watching";
  if (score >= 70) return "drifting";
  return "blocked";
}

function toneFromLatency(latencyMs: number): ObservatoryTone {
  if (latencyMs <= 1_200) return "healthy";
  if (latencyMs <= 2_000) return "watching";
  if (latencyMs <= 4_000) return "drifting";
  return "blocked";
}

function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
  );
  return sorted[index] ?? 0;
}

function formatLatency(ms: number): string {
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(2)} s`;
  return `${Math.round(ms)} ms`;
}

function formatTime(ms: number): string {
  const d = new Date(ms);
  return `${String(d.getUTCHours()).padStart(2, "0")}:${String(
    d.getUTCMinutes(),
  ).padStart(2, "0")}:${String(d.getUTCSeconds()).padStart(2, "0")}`;
}

function traceTone(trace: TraceSummary): ObservatoryTone {
  if (trace.status === "error") return "blocked";
  return toneFromLatency(trace.duration_ns / 1_000_000);
}

function severityRank(severity: ObservatoryAnomaly["severity"]): number {
  return {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  }[severity];
}

function confidenceForAnomaly(
  anomaly: ObservatoryAnomaly,
): Pick<ObservatoryRecommendation, "confidence" | "confidenceLevel" | "tone"> {
  if (anomaly.severity === "critical") {
    return { confidence: 92, confidenceLevel: "high", tone: "danger" };
  }
  if (anomaly.severity === "high") {
    return { confidence: 86, confidenceLevel: "medium", tone: "warning" };
  }
  if (anomaly.severity === "medium") {
    return { confidence: 74, confidenceLevel: "medium", tone: "warning" };
  }
  return { confidence: 61, confidenceLevel: "low", tone: "info" };
}

function buildRecommendation(args: {
  anomalies: readonly ObservatoryAnomaly[];
  metrics: readonly ObservatoryMetric[];
  degradedReason?: string | undefined;
}): ObservatoryRecommendation {
  if (args.degradedReason) {
    return {
      title: "Connect telemetry before operating",
      body:
        "No operating recommendation is ranked until traces, usage, inbox, and incidents load from cp-api.",
      observed: args.degradedReason,
      intended:
        "The Observatory should only recommend action from live trace, usage, inbox, and incident evidence.",
      source: "observatory/backend-required",
      confidence: 0,
      confidenceLevel: "unsupported",
      tone: "warning",
    };
  }

  const actionableAnomalies = [...args.anomalies].filter(
    (anomaly) =>
      anomaly.id !== "live_no_anomalies" &&
      anomaly.id !== "telemetry_not_loaded",
  );
  const topAnomaly = actionableAnomalies.sort(
    (a, b) => severityRank(b.severity) - severityRank(a.severity),
  )[0];
  if (topAnomaly) {
    return {
      title: "Next best operating action",
      body: topAnomaly.nextAction,
      observed: topAnomaly.observedBehavior,
      intended: topAnomaly.intendedBehavior,
      source: `observatory/anomaly/${topAnomaly.id}`,
      ...confidenceForAnomaly(topAnomaly),
    };
  }

  const firstMetric = args.metrics.find(
    (metric) => metric.tone !== "healthy",
  ) ?? args.metrics[0];
  if (firstMetric) {
    return {
      title: "Next best operating action",
      body: firstMetric.nextAction,
      observed: `${firstMetric.label}: ${firstMetric.value}. ${firstMetric.delta}`,
      intended:
        "Keep the live window inside the agent commitment before promoting more traffic.",
      source: `observatory/metric/${firstMetric.id}`,
      confidence: firstMetric.tone === "healthy" ? 66 : 78,
      confidenceLevel: firstMetric.tone === "healthy" ? "low" : "medium",
      tone: firstMetric.tone === "healthy" ? "success" : "warning",
    };
  }

  return {
    title: "No operating recommendation available",
    body:
      "Load live traces, usage, inbox, and incidents before ranking the next action.",
    observed: "No live operating facts are present in the model.",
    intended: "Observability recommendations must be evidence-backed.",
    source: "observatory/empty",
    confidence: 0,
    confidenceLevel: "unsupported",
    tone: "warning",
  };
}

function tracesForAgent(traces: readonly TraceSummary[]) {
  const groups = new Map<string, TraceSummary[]>();
  for (const trace of traces) {
    const list = groups.get(trace.agent_id) ?? [];
    list.push(trace);
    groups.set(trace.agent_id, list);
  }
  return groups;
}

function usageCentsByAgent(
  records: readonly UsageRecord[],
): Map<string, number> {
  const month = monthBoundsUTC(Date.now());
  const summary = summariseCosts([...records], {
    workspace_id: records[0]?.workspace_id ?? "",
    period_start_ms: month.period_start_ms,
    period_end_ms: month.period_end_ms,
  });
  return new Map(
    summary.by_agent.map((agent) => [agent.agent_id, agent.cents]),
  );
}

export function buildObservatoryModel(args: {
  workspaceId: string;
  traces: readonly TraceSummary[];
  usage: readonly UsageRecord[];
  inbox: readonly InboxItem[];
  incidents?: readonly IncidentRecord[];
  nowMs: number;
  degradedReason?: string | undefined;
}): ObservatoryModel {
  const traces = [...args.traces].sort(
    (a, b) => b.started_at_ms - a.started_at_ms,
  );
  const totalTraces = traces.length;
  const errorCount = traces.filter((trace) => trace.status === "error").length;
  const okRate =
    totalTraces === 0 ? 100 : ((totalTraces - errorCount) / totalTraces) * 100;
  const latenciesMs = traces.map((trace) => trace.duration_ns / 1_000_000);
  const p95LatencyMs = percentile(latenciesMs, 95);
  const openInbox = args.inbox.filter((item) => item.status !== "resolved");
  const escalations = openInbox.length;
  const escalationRate =
    totalTraces === 0 ? 0 : (escalations / Math.max(1, totalTraces)) * 100;
  const month = monthBoundsUTC(args.nowMs);
  const costSummary = summariseCosts([...args.usage], {
    workspace_id: args.workspaceId,
    period_start_ms: month.period_start_ms,
    period_end_ms: month.period_end_ms,
  });
  const kpis = computeWorkspaceKpis([...args.usage], {
    workspace_id: args.workspaceId,
    now_ms: args.nowMs,
  });
  const retrievals = args.usage
    .filter((record) => record.metric === "retrievals")
    .reduce((sum, record) => sum + record.quantity, 0);
  const turns = args.usage.reduce(
    (sum, record) => sum + (record.turn_count ?? 0),
    0,
  );
  const costPerTurnCents =
    turns > 0 ? costSummary.total_cents / turns : costSummary.total_cents;
  const knowledgeScore =
    totalTraces === 0 ? 100 : Math.min(100, (retrievals / totalTraces) * 100);

  const anomalies: ObservatoryAnomaly[] = [];
  if (errorCount > 0) {
    anomalies.push({
      id: "live_trace_errors",
      title: "Production trace errors need triage",
      severity: errorCount >= 5 ? "critical" : "high",
      evidence: `${errorCount} of ${totalTraces} recent traces ended in error.`,
      affectedObject: "behavior/runtime_error_handling",
      observedBehavior: `${errorCount} of ${totalTraces} recent production traces errored before completing the turn.`,
      intendedBehavior:
        "Production turns should either complete the committed behavior or fail into a recoverable handoff with trace and eval evidence.",
      editSurface: "behavior",
      nextAction:
        "Open the failed trace cluster and promote one failure into an eval case.",
      owner: "Runtime owner",
      traceQuery: "status:error",
    });
  }
  if (p95LatencyMs > 2_000) {
    anomalies.push({
      id: "live_latency_budget",
      title: "P95 latency is outside the interactive budget",
      severity: p95LatencyMs > 4_000 ? "high" : "medium",
      evidence: `Recent p95 is ${formatLatency(p95LatencyMs)} across ${totalTraces} traces.`,
      affectedObject: "latency budget",
      observedBehavior: `Recent p95 is ${formatLatency(p95LatencyMs)} across ${totalTraces} production traces.`,
      intendedBehavior:
        "Interactive channels should stay inside the committed latency budget before canary or ramp expansion.",
      editSurface: "traces",
      nextAction:
        "Open the latency budget view and target the slowest span family first.",
      owner: "Platform integrations",
      traceQuery: "duration_ms:>2000",
    });
  }
  if (openInbox.length > 0) {
    anomalies.push({
      id: "live_handoff_queue",
      title: "Human handoff queue has unresolved work",
      severity: openInbox.length >= 10 ? "high" : "medium",
      evidence: `${openInbox.length} escalations are pending or claimed.`,
      affectedObject: "operator inbox",
      observedBehavior: `${openInbox.length} handoff${openInbox.length === 1 ? "" : "s"} are still pending or claimed in the live queue.`,
      intendedBehavior:
        "Human handoffs should route to an owner, resolve with evidence, and become regression coverage when they reveal a behavior gap.",
      editSurface: "inbox",
      nextAction:
        "Route the oldest pending escalation, then convert the final resolution into an eval.",
      owner: "Support operations",
      traceQuery: "handoff:open",
    });
  }
  const activeIncidents = [...(args.incidents ?? [])].filter(
    (incident) =>
      incident.status !== "resolved" && incident.status !== "archived",
  );
  if (activeIncidents.length > 0) {
    const highest = activeIncidents[0]!;
    anomalies.unshift({
      id: `incident_${highest.id}`,
      title: "Incident response is active",
      severity: highest.severity,
      evidence: `${highest.trigger}; ${highest.affected_conversation_count} conversations flagged.`,
      affectedObject: `incident/${highest.id}`,
      observedBehavior: `${highest.affected_conversation_count} conversation${highest.affected_conversation_count === 1 ? "" : "s"} were flagged by ${highest.trigger}.`,
      intendedBehavior:
        "Incident response should contain the rollout, attach affected traces, seed regression evals, and stage a fix Change Package before traffic resumes.",
      editSurface: "incidents",
      nextAction:
        highest.candidate_eval_suite_id === null
          ? "Seed candidate regression evals from the incident report."
          : "Review the seeded eval suite before staging the fix.",
      owner: highest.created_by,
      traceQuery: highest.affected_trace_ids.join(" OR "),
      evalCandidateRef: highest.candidate_eval_suite_id ?? undefined,
    });
  }
  if (anomalies.length === 0) {
    if (
      totalTraces === 0 &&
      args.usage.length === 0 &&
      openInbox.length === 0
    ) {
      anomalies.push({
        id: "telemetry_not_loaded",
        title: "No production telemetry loaded",
        severity: "low",
        evidence:
          "No traces, usage records, inbox items, or incidents were returned for this workspace.",
        affectedObject: "workspace telemetry",
        observedBehavior:
          "The Observatory has no live traces, usage records, inbox items, or incidents to inspect.",
        intendedBehavior:
          "The Observatory should only make operating claims from connected telemetry, never from placeholder liveness.",
        editSurface: "observe",
        nextAction:
          "Connect cp-api telemetry before treating this observatory as live.",
        owner: "Workspace owner",
        traceQuery: "workspace:empty",
      });
    } else {
      anomalies.push({
        id: "live_no_anomalies",
        title: "No active production anomalies in the live window",
        severity: "low",
        evidence: `${totalTraces} traces, ${openInbox.length} open escalations, ${formatUSD(
          costSummary.total_cents,
        )} month-to-date usage.`,
        affectedObject: "workspace live window",
        observedBehavior: `${totalTraces} traces, ${openInbox.length} open escalations, and ${formatUSD(
          costSummary.total_cents,
        )} month-to-date usage are inside the current live window.`,
        intendedBehavior:
          "Production should remain observable, regression-backed, and ready for rollback while canary traffic bakes.",
        editSurface: "observe",
        nextAction:
          "Keep the production tail pinned while the next canary bakes.",
        owner: "Workspace owner",
        traceQuery: "status:any",
      });
    }
  }

  const groupedTraces = tracesForAgent(traces);
  const costByAgent = usageCentsByAgent(args.usage);
  const agents: AmbientAgentHealth[] = [...groupedTraces.entries()].map(
    ([agentId, agentTraces]) => {
      const agentErrors = agentTraces.filter(
        (trace) => trace.status === "error",
      ).length;
      const evalPassRate =
        agentTraces.length === 0
          ? 100
          : Math.round(
              ((agentTraces.length - agentErrors) / agentTraces.length) * 100,
            );
      const agentLatency = percentile(
        agentTraces.map((trace) => trace.duration_ns / 1_000_000),
        95,
      );
      const agentEscalations = args.inbox.filter(
        (item) => item.agent_id === agentId && item.status !== "resolved",
      ).length;
      return {
        id: agentId,
        name: agentTraces[0]?.agent_name || agentId,
        evalPassRate,
        p95LatencyMs: Math.round(agentLatency),
        costDeltaPct: Math.round((costByAgent.get(agentId) ?? 0) / 100),
        escalationRate:
          agentTraces.length === 0
            ? 0
            : Math.round((agentEscalations / agentTraces.length) * 1000) / 10,
        tone: toneFromScore(evalPassRate),
      };
    },
  );

  const metrics: ObservatoryMetric[] = [
    {
      id: "quality",
      label: "Quality",
      value: `${okRate.toFixed(1)}%`,
      delta: `${errorCount} errored turns in ${totalTraces} live traces`,
      tone: toneFromScore(okRate),
      nextAction:
        errorCount > 0
          ? "Open the highest-cost failed trace and save it as a regression case."
          : "Keep replaying production traces before every promotion.",
    },
    {
      id: "latency",
      label: "P95 latency",
      value: formatLatency(p95LatencyMs),
      delta: `${totalTraces} trace sample${totalTraces === 1 ? "" : "s"}`,
      tone: toneFromLatency(p95LatencyMs),
      nextAction:
        p95LatencyMs > 1_200
          ? "Open the latency budget visualizer for the slowest recent turn."
          : "Hold the current latency budget as canary traffic increases.",
    },
    {
      id: "cost",
      label: "Cost per turn",
      value: formatUSD(costPerTurnCents),
      delta: `${formatDeltaPercent(kpis.mtd_cents, kpis.prev_month_cents)} vs prior month`,
      tone: costPerTurnCents <= 5 ? "healthy" : "watching",
      nextAction:
        turns > 0
          ? "Review the highest-cost agent line before increasing traffic."
          : "Emit turn_count in usage events so cost per turn becomes precise.",
    },
    {
      id: "knowledge",
      label: "Retrieval signal",
      value: `${Math.round(retrievals).toLocaleString()}`,
      delta: `${knowledgeScore.toFixed(0)} retrievals per 100 traces`,
      tone: toneFromScore(knowledgeScore),
      nextAction:
        retrievals > 0
          ? "Open missed-retrieval traces and convert them into inverse retrieval checks."
          : "Connect retrieval telemetry so knowledge health stops being inferred.",
    },
    {
      id: "handoff",
      label: "Escalation rate",
      value: `${escalationRate.toFixed(1)}%`,
      delta: `${openInbox.length} unresolved inbox item${openInbox.length === 1 ? "" : "s"}`,
      tone: escalationRate <= 5 ? "healthy" : "watching",
      nextAction:
        openInbox.length > 0
          ? "Resolve the oldest handoff and turn the resolution into an eval."
          : "Keep the inbox clear while monitoring production tail drift.",
    },
    {
      id: "deploy",
      label: "Deploy state",
      value: "Live window",
      delta: `${formatUSD(kpis.projected_eom_cents)} projected month-end`,
      tone: anomalies.some((anomaly) => anomaly.severity === "critical")
        ? "blocked"
        : "watching",
      nextAction:
        "Use this live posture as the pre-promote read before increasing canary traffic.",
    },
  ];
  const visibleMetrics = args.degradedReason
    ? metrics.map((metric) => ({
        ...metric,
        tone: "blocked" as const,
        delta: "Telemetry backend not connected",
        nextAction:
          "Connect cp-api telemetry before treating this observatory as live.",
      }))
    : metrics;

  return {
    metrics: visibleMetrics,
    anomalies,
    incidents: activeIncidents,
    tail: traces.slice(0, 8).map((trace) => ({
      id: trace.id,
      time: formatTime(trace.started_at_ms),
      channel: "Web",
      summary:
        trace.status === "error"
          ? `${trace.root_name} failed; inspect trace before replay.`
          : `${trace.root_name} completed in ${formatLatency(trace.duration_ns / 1_000_000)}.`,
      traceId: trace.id,
      status: traceTone(trace),
    })),
    agents,
    recommendation: buildRecommendation({
      anomalies,
      metrics: visibleMetrics,
      degradedReason: args.degradedReason,
    }),
    degradedReason: args.degradedReason,
  };
}

export async function fetchObservatoryModel(
  workspaceId: string,
  opts: ObservatoryClientOptions = {},
): Promise<ObservatoryModel> {
  if (!hasCpApiBase(opts.baseUrl)) {
    return buildObservatoryModel({
      workspaceId,
      traces: [],
      usage: [],
      inbox: [],
      incidents: [],
      nowMs: Date.now(),
      degradedReason:
        "LOOP_CP_API_BASE_URL is required for live Observatory telemetry.",
    });
  }
  const nowMs = Date.now();
  const month = monthBoundsUTC(nowMs);
  let traces: TraceSummary[];
  let usage: UsageRecord[];
  let inbox: InboxItem[];
  let incidents: IncidentRecord[];
  try {
    [traces, usage, inbox, incidents] = await Promise.all([
      searchTraces(workspaceId, { page_size: 100 }, opts).then(
        (result) => result.traces,
      ),
      fetchUsageRecords(
        workspaceId,
        { start_ms: month.period_start_ms, end_ms: month.period_end_ms },
        opts,
      ),
      listInbox(workspaceId, opts).then((result) => result.items),
      listWorkspaceIncidents(workspaceId, opts).then((result) => result.items),
    ]);
  } catch (error) {
    return buildObservatoryModel({
      workspaceId,
      traces: [],
      usage: [],
      inbox: [],
      incidents: [],
      nowMs,
      degradedReason:
        error instanceof Error
          ? `Live Observatory telemetry is unavailable: ${error.message}`
          : "Live Observatory telemetry is unavailable.",
    });
  }
  return buildObservatoryModel({
    workspaceId,
    traces,
    usage,
    inbox,
    incidents,
    nowMs,
  });
}

export async function pinObservatoryMetric(
  workspaceId: string,
  metric: ObservatoryMetric,
  opts: ObservatoryMutationOptions = {},
): Promise<ObservatoryDashboardLayout> {
  return cpJson<ObservatoryDashboardLayout>(
    `/workspaces/${encodeURIComponent(workspaceId)}/dashboards`,
    {
      ...opts,
      method: "POST",
      allowFallback: opts.allowFixture === true,
      body: {
        name: `${metric.label} watch`,
        layout: [
          {
            source_type: "observatory_metric",
            source_id: metric.id,
            title: metric.label,
          },
        ],
        shared_with: [],
      },
      fallback: {
        id: `dash_local_${metric.id}`,
        name: `${metric.label} watch`,
        layout: [
          {
            source_type: "observatory_metric",
            source_id: metric.id,
            title: metric.label,
          },
        ],
        shared_with: [],
      },
    },
  );
}

export async function createObservatoryAnomalyTask(
  workspaceId: string,
  anomaly: ObservatoryAnomaly,
  opts: ObservatoryMutationOptions = {},
): Promise<ObservatoryActionRef> {
  return cpJson<ObservatoryActionRef>(
    `/workspaces/${encodeURIComponent(
      workspaceId,
    )}/observatory/anomalies/${encodeURIComponent(anomaly.id)}/tasks`,
    {
      ...opts,
      method: "POST",
      allowFallback: opts.allowFixture === true,
      body: {
        title: anomaly.title,
        evidence: anomaly.evidence,
        affected_object: anomaly.affectedObject,
        observed_behavior: anomaly.observedBehavior,
        intended_behavior: anomaly.intendedBehavior,
        edit_surface: anomaly.editSurface,
        next_action: anomaly.nextAction,
        owner: anomaly.owner,
        trace_query: anomaly.traceQuery,
      },
      fallback: {
        id: `task_local_${anomaly.id}`,
        evidence: anomaly.evidence,
      },
    },
  );
}

export async function createObservatoryAnomalyEvalCase(
  workspaceId: string,
  anomaly: ObservatoryAnomaly,
  opts: ObservatoryMutationOptions = {},
): Promise<ObservatoryActionRef> {
  return cpJson<ObservatoryActionRef>(
    `/workspaces/${encodeURIComponent(
      workspaceId,
    )}/observatory/anomalies/${encodeURIComponent(anomaly.id)}/eval-cases`,
    {
      ...opts,
      method: "POST",
      allowFallback: opts.allowFixture === true,
      body: {
        source_type: "incident_cluster",
        source_ref: anomaly.id,
        affected_object: anomaly.affectedObject,
        observed_behavior: anomaly.observedBehavior,
        expected_behavior: anomaly.intendedBehavior,
        edit_surface: anomaly.editSurface,
        evidence: anomaly.evidence,
        trace_query: anomaly.traceQuery,
      },
      fallback: {
        id: `eval_local_${anomaly.id}`,
        evidence: anomaly.evidence,
      },
    },
  );
}

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
import { targetUxFixtures } from "@/lib/target-ux";
import {
  searchTraces,
  type TraceSummary,
  type TracesClientOptions,
} from "@/lib/traces";

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
  nextAction: string;
  owner: string;
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

export interface ObservatoryModel {
  metrics: readonly ObservatoryMetric[];
  anomalies: readonly ObservatoryAnomaly[];
  tail: readonly ProductionTailEvent[];
  agents: readonly AmbientAgentHealth[];
}

export interface ObservatoryClientOptions
  extends UsageClientOptions,
    TracesClientOptions,
    InboxClientOptions {}

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

function tracesForAgent(traces: readonly TraceSummary[]) {
  const groups = new Map<string, TraceSummary[]>();
  for (const trace of traces) {
    const list = groups.get(trace.agent_id) ?? [];
    list.push(trace);
    groups.set(trace.agent_id, list);
  }
  return groups;
}

function usageCentsByAgent(records: readonly UsageRecord[]): Map<string, number> {
  const month = monthBoundsUTC(Date.now());
  const summary = summariseCosts([...records], {
    workspace_id: records[0]?.workspace_id ?? "",
    period_start_ms: month.period_start_ms,
    period_end_ms: month.period_end_ms,
  });
  return new Map(summary.by_agent.map((agent) => [agent.agent_id, agent.cents]));
}

export function buildObservatoryModel(args: {
  workspaceId: string;
  traces: readonly TraceSummary[];
  usage: readonly UsageRecord[];
  inbox: readonly InboxItem[];
  nowMs: number;
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
      nextAction: "Open the failed trace cluster and promote one failure into an eval case.",
      owner: "Runtime owner",
    });
  }
  if (p95LatencyMs > 2_000) {
    anomalies.push({
      id: "live_latency_budget",
      title: "P95 latency is outside the interactive budget",
      severity: p95LatencyMs > 4_000 ? "high" : "medium",
      evidence: `Recent p95 is ${formatLatency(p95LatencyMs)} across ${totalTraces} traces.`,
      nextAction: "Open the latency budget view and target the slowest span family first.",
      owner: "Platform integrations",
    });
  }
  if (openInbox.length > 0) {
    anomalies.push({
      id: "live_handoff_queue",
      title: "Human handoff queue has unresolved work",
      severity: openInbox.length >= 10 ? "high" : "medium",
      evidence: `${openInbox.length} escalations are pending or claimed.`,
      nextAction: "Route the oldest pending escalation, then convert the final resolution into an eval.",
      owner: "Support operations",
    });
  }
  if (anomalies.length === 0) {
    anomalies.push({
      id: "live_no_anomalies",
      title: "No active production anomalies in the live window",
      severity: "low",
      evidence: `${totalTraces} traces, ${openInbox.length} open escalations, ${formatUSD(
        costSummary.total_cents,
      )} month-to-date usage.`,
      nextAction: "Keep the production tail pinned while the next canary bakes.",
      owner: "Workspace owner",
    });
  }

  const groupedTraces = tracesForAgent(traces);
  const costByAgent = usageCentsByAgent(args.usage);
  const agents: AmbientAgentHealth[] =
    groupedTraces.size > 0
      ? [...groupedTraces.entries()].map(([agentId, agentTraces]) => {
          const agentErrors = agentTraces.filter(
            (trace) => trace.status === "error",
          ).length;
          const evalPassRate =
            agentTraces.length === 0
              ? 100
              : Math.round(
                  ((agentTraces.length - agentErrors) / agentTraces.length) *
                    100,
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
                : Math.round((agentEscalations / agentTraces.length) * 1000) /
                  10,
            tone: toneFromScore(evalPassRate),
          };
        })
      : targetUxFixtures.agents.slice(0, 2).map((agent) => ({
          id: agent.id,
          name: agent.name,
          evalPassRate: 100,
          p95LatencyMs: 0,
          costDeltaPct: 0,
          escalationRate: 0,
          tone: "watching" as const,
        }));

  return {
    metrics: [
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
    ],
    anomalies,
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
  };
}

export async function fetchObservatoryModel(
  workspaceId: string,
  opts: ObservatoryClientOptions = {},
): Promise<ObservatoryModel> {
  if (!hasCpApiBase(opts.baseUrl)) return OBSERVATORY_MODEL;
  const nowMs = Date.now();
  const month = monthBoundsUTC(nowMs);
  const [traces, usage, inbox] = await Promise.all([
    searchTraces(workspaceId, { page_size: 100 }, opts).then(
      (result) => result.traces,
    ),
    fetchUsageRecords(
      workspaceId,
      { start_ms: month.period_start_ms, end_ms: month.period_end_ms },
      opts,
    ),
    listInbox(workspaceId, opts).then((result) => result.items),
  ]);
  return buildObservatoryModel({
    workspaceId,
    traces,
    usage,
    inbox,
    nowMs,
  });
}

export const OBSERVATORY_MODEL: ObservatoryModel = {
  metrics: [
    {
      id: "quality",
      label: "Quality",
      value: "96.4%",
      delta: "+1.8 from baseline",
      tone: "healthy",
      nextAction: "Keep the refund replay suite pinned to deploy preflight.",
    },
    {
      id: "latency",
      label: "P95 latency",
      value: "1.18 s",
      delta: "-180 ms under draft",
      tone: "watching",
      nextAction: "Batch entitlement lookup with order lookup to save another 90 ms.",
    },
    {
      id: "cost",
      label: "Cost per turn",
      value: "$0.043",
      delta: "-7% against v23.1.4",
      tone: "healthy",
      nextAction: "Cache low-risk policy context on repeat refund turns.",
    },
    {
      id: "knowledge",
      label: "Citation health",
      value: "91%",
      delta: "6 metadata gaps",
      tone: "drifting",
      nextAction: "Open Inverse Retrieval for the region metadata cluster.",
    },
    {
      id: "handoff",
      label: "Escalation rate",
      value: "4.2%",
      delta: "+0.6 after draft",
      tone: "watching",
      nextAction: "Review legal-threat scenes before canary reaches 25%.",
    },
    {
      id: "deploy",
      label: "Deploy state",
      value: "12% canary",
      delta: "1 approval missing",
      tone: "watching",
      nextAction: "Ask Trust Review to approve the Spanish refund regression fix.",
    },
  ],
  anomalies: [
    {
      id: "anom_legal_synonym",
      title: "Attorney synonym misses legal handoff rule",
      severity: "high",
      evidence: "17 production-like variants failed in replay and persona simulation.",
      nextAction: "Patch the escalation classifier, then replay the affected scene.",
      owner: "CX Policy",
    },
    {
      id: "anom_region_metadata",
      title: "Region metadata absent on renewal chunks",
      severity: "medium",
      evidence: "6 missed retrievals should have cited refund_policy_2026.pdf.",
      nextAction: "Backfill region metadata and regenerate retrieval evals.",
      owner: "Knowledge Lead",
    },
    {
      id: "anom_tool_wait",
      title: "Tool wait exceeds voice budget",
      severity: "medium",
      evidence: "lookup_order adds 180 ms where the voice budget is 160 ms.",
      nextAction: "Use preview batching before enabling phone canary.",
      owner: "Platform Integrations",
    },
  ],
  tail: [
    {
      id: "tail_1",
      time: "12:04:22",
      channel: "Web",
      summary: "Refund refusal cited policy and created handoff.",
      traceId: "trace_refund_742",
      status: "healthy",
    },
    {
      id: "tail_2",
      time: "12:05:10",
      channel: "Voice",
      summary: "Caller interrupted TTS; barge-in preserved renewal context.",
      traceId: "trace_voice_119",
      status: "watching",
    },
    {
      id: "tail_3",
      time: "12:06:03",
      channel: "Slack",
      summary: "Attorney wording skipped legal handoff under draft replay.",
      traceId: "trace_legal_synonym",
      status: "drifting",
    },
    {
      id: "tail_4",
      time: "12:06:44",
      channel: "WhatsApp",
      summary: "Spanish paraphrase passed citation and handoff eval.",
      traceId: "trace_spanish_pass",
      status: "healthy",
    },
  ],
  agents: targetUxFixtures.agents.map((agent, index) => ({
    id: agent.id,
    name: agent.name,
    evalPassRate: agent.evalPassRate,
    p95LatencyMs: agent.p95LatencyMs,
    costDeltaPct: index === 0 ? -7 : 4,
    escalationRate: index === 0 ? 4.2 : 7.8,
    tone: agent.trust === "healthy" ? "healthy" : "watching",
  })),
};

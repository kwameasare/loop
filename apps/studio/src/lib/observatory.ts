import { targetUxFixtures } from "@/lib/target-ux";

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

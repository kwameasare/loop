export type LatencySegmentId =
  | "channel_ingress"
  | "asr"
  | "model"
  | "retrieval"
  | "tool_calls"
  | "memory"
  | "orchestration"
  | "tts"
  | "channel_delivery";

export interface LatencyBudgetSegment {
  id: LatencySegmentId;
  label: string;
  ms: number;
  evidence: string;
  state: "ready" | "unsupported";
}

export interface LatencyBudgetSuggestion {
  id: string;
  label: string;
  expectedMsDelta: number;
  costImpactUsd: number;
  qualityImpact: string;
  evalImpact: string;
  evidence: string;
  state: "draft" | "blocked";
}

export interface LatencyBudgetModel {
  scenario: string;
  dataSource: "planning" | "trace" | "unavailable";
  provenance: string;
  targetMs: number;
  totalMs: number;
  segments: LatencyBudgetSegment[];
  suggestions: LatencyBudgetSuggestion[];
}

export interface BuildLatencyBudgetOptions {
  scenario?: string | undefined;
  provenance?: string | undefined;
  dataSource?: LatencyBudgetModel["dataSource"] | undefined;
}

export function formatMs(ms: number): string {
  return `${Math.round(ms).toLocaleString()} ms`;
}

export function formatSignedMs(ms: number): string {
  if (ms === 0) return "0 ms";
  return `${ms > 0 ? "+" : ""}${Math.round(ms).toLocaleString()} ms`;
}

export function formatSignedUsd(amount: number): string {
  if (amount === 0) return "$0.0000";
  const sign = amount > 0 ? "+" : "-";
  return `${sign}$${Math.abs(amount).toFixed(4)}`;
}

export function buildLatencyBudgetModel(
  targetMs = 800,
  options: BuildLatencyBudgetOptions = {},
): LatencyBudgetModel {
  const provenance =
    options.provenance ??
    "latency planning model; replace with trace spans when a trace is selected";
  const segments: LatencyBudgetSegment[] = [
    {
      id: "channel_ingress",
      label: "Channel ingress",
      ms: 45,
      evidence: `${provenance}: channel ingress estimate`,
      state: "ready",
    },
    {
      id: "asr",
      label: "ASR",
      ms: 0,
      evidence: `${provenance}: no speech input in this planning model`,
      state: "unsupported",
    },
    {
      id: "model",
      label: "Model",
      ms: 428,
      evidence: `${provenance}: model span estimate`,
      state: "ready",
    },
    {
      id: "retrieval",
      label: "Retrieval",
      ms: 133,
      evidence: `${provenance}: retrieval span estimate`,
      state: "ready",
    },
    {
      id: "tool_calls",
      label: "Tool calls",
      ms: 243,
      evidence: `${provenance}: tool-call span estimate`,
      state: "ready",
    },
    {
      id: "memory",
      label: "Memory",
      ms: 37,
      evidence: `${provenance}: memory write estimate`,
      state: "ready",
    },
    {
      id: "orchestration",
      label: "Orchestration",
      ms: 122,
      evidence: `${provenance}: orchestration estimate`,
      state: "ready",
    },
    {
      id: "tts",
      label: "TTS",
      ms: 0,
      evidence: `${provenance}: no speech output in this planning model`,
      state: "unsupported",
    },
    {
      id: "channel_delivery",
      label: "Channel delivery",
      ms: 22,
      evidence: `${provenance}: delivery estimate`,
      state: "ready",
    },
  ];
  const totalMs = segments.reduce((sum, segment) => sum + segment.ms, 0);
  return {
    scenario: options.scenario ?? "Static planning scenario",
    dataSource: options.dataSource ?? "planning",
    provenance,
    targetMs,
    totalMs,
    segments,
    suggestions: [
      {
        id: "cache_pricing_policy",
        label: "Cache `pricing_policy` retrieval",
        expectedMsDelta: -90,
        costImpactUsd: -0.0004,
        qualityImpact:
          "No expected answer-quality change for cached policy chunks.",
        evalImpact: "Run retrieval.final_sale_refund before apply.",
        evidence: "Retrieval span and KB eval coverage",
        state: "draft",
      },
      {
        id: "smaller_classifier",
        label: "Use smaller model for classification",
        expectedMsDelta: -280,
        costImpactUsd: -0.003,
        qualityImpact: "Possible -1.2 point routing eval impact.",
        evalImpact: "Blocked until routing_regression stays above 0.95.",
        evidence: "Eval Foundry latency_le scorer and model line item",
        state: "blocked",
      },
      {
        id: "remove_second_iteration",
        label: "Remove second model iteration in `triage`",
        expectedMsDelta: -410,
        costImpactUsd: -0.0062,
        qualityImpact: "May reduce explanation detail on complex disputes.",
        evalImpact: "Requires support_smoke and refund_window_basic pass.",
        evidence: "Trace span count plus cost line item math",
        state: "draft",
      },
    ],
  };
}

export function buildUnavailableLatencyBudgetModel(
  targetMs = 800,
  reason =
    "Span-level latency is not available for this surface. Open a trace to inspect latency budgets backed by runtime spans.",
): LatencyBudgetModel {
  return {
    scenario: "Trace latency unavailable",
    dataSource: "unavailable",
    provenance: reason,
    targetMs,
    totalMs: 0,
    segments: [],
    suggestions: [],
  };
}

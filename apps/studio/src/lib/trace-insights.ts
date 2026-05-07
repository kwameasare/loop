import { cpJson, type UxWireupClientOptions } from "@/lib/ux-wireup";
import type { Trace } from "@/lib/traces";

export interface LatencyBudgetSpan {
  id: string;
  label: string;
  ms: number;
  kind: string;
}

export interface LatencyBudgetSuggestion {
  id: string;
  label: string;
  saves_ms: number;
  quality_delta: number;
  evidence_ref: string;
}

export interface LatencyBudgetModel {
  trace_id: string;
  target_latency_ms: number;
  total_latency_ms: number;
  gap_ms: number;
  spans: LatencyBudgetSpan[];
  suggestions: LatencyBudgetSuggestion[];
}

export interface ContextAblationItem {
  id: "prompt_sections" | "kb_chunks" | "memory" | "examples" | string;
  label: string;
  enabled: boolean;
  cost_delta_pct: number;
  latency_delta_ms: number;
  quality_delta: number;
  evidence_ref: string;
}

export interface ContextAblationModel {
  turn_id: string;
  items: ContextAblationItem[];
}

function fallbackLatencyBudget(trace: Trace, targetLatencyMs: number): LatencyBudgetModel {
  const spans = trace.spans.map<LatencyBudgetSpan>((span) => ({
    id: span.id,
    label: span.name,
    ms: Math.max(1, Math.round((span.end_ns - span.start_ns) / 1_000_000)),
    kind: span.category,
  }));
  const total = spans.reduce((sum, span) => sum + span.ms, 0);
  return {
    trace_id: trace.id,
    target_latency_ms: targetLatencyMs,
    total_latency_ms: total,
    gap_ms: Math.max(0, total - targetLatencyMs),
    spans,
    suggestions: [
      {
        id: "swap_model",
        label: "Swap to fast draft model",
        saves_ms: 280,
        quality_delta: -0.02,
        evidence_ref: `${trace.id}/latency/llm`,
      },
      {
        id: "cache_retrieval",
        label: "Cache repeated KB query",
        saves_ms: 90,
        quality_delta: 0,
        evidence_ref: `${trace.id}/latency/retrieval`,
      },
    ],
  };
}

export async function fetchLatencyBudget(
  agentId: string,
  trace: Trace,
  targetLatencyMs: number,
  opts: UxWireupClientOptions = {},
): Promise<LatencyBudgetModel> {
  return cpJson<LatencyBudgetModel>(
    `/agents/${encodeURIComponent(agentId)}/latency-budget`,
    {
      ...opts,
      method: "POST",
      body: {
        trace_id: trace.id,
        target_latency_ms: targetLatencyMs,
      },
      fallback: fallbackLatencyBudget(trace, targetLatencyMs),
    },
  );
}

export async function fetchContextAblation(
  agentId: string,
  turnId: string,
  toggles: Record<string, boolean>,
  opts: UxWireupClientOptions = {},
): Promise<ContextAblationModel> {
  return cpJson<ContextAblationModel>(
    `/agents/${encodeURIComponent(agentId)}/context-ablation`,
    {
      ...opts,
      method: "POST",
      body: { turn_id: turnId, toggles },
      fallback: {
        turn_id: turnId,
        items: [
          {
            id: "prompt_sections",
            label: "Long-tail prompt sections",
            enabled: toggles.prompt_sections ?? true,
            cost_delta_pct: toggles.prompt_sections === false ? -14 : 0,
            latency_delta_ms: toggles.prompt_sections === false ? -120 : 0,
            quality_delta: toggles.prompt_sections === false ? -0.01 : 0,
            evidence_ref: `${turnId}/context/prompt`,
          },
          {
            id: "kb_chunks",
            label: "Retrieved KB chunks",
            enabled: toggles.kb_chunks ?? true,
            cost_delta_pct: toggles.kb_chunks === false ? -9 : 0,
            latency_delta_ms: toggles.kb_chunks === false ? -90 : 0,
            quality_delta: toggles.kb_chunks === false ? -0.08 : 0,
            evidence_ref: `${turnId}/context/kb`,
          },
          {
            id: "memory",
            label: "Durable memory",
            enabled: toggles.memory ?? true,
            cost_delta_pct: toggles.memory === false ? -3 : 0,
            latency_delta_ms: toggles.memory === false ? -45 : 0,
            quality_delta: toggles.memory === false ? -0.02 : 0,
            evidence_ref: `${turnId}/context/memory`,
          },
          {
            id: "examples",
            label: "Few-shot examples",
            enabled: toggles.examples ?? true,
            cost_delta_pct: toggles.examples === false ? -11 : 0,
            latency_delta_ms: toggles.examples === false ? -70 : 0,
            quality_delta: toggles.examples === false ? -0.03 : 0,
            evidence_ref: `${turnId}/context/examples`,
          },
        ],
      },
    },
  );
}

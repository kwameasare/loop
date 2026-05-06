import type { Span, Trace, TraceJsonValue, TracePayload } from "@/lib/traces";

export interface TraceIdentity {
  traceId: string;
  version: string;
  snapshotId: string;
  environment: string;
}

export interface TraceScrubberFrame {
  id: string;
  index: number;
  spanId: string;
  spanName: string;
  category: Span["category"];
  status: Span["status"];
  atNs: number;
  position: number;
  label: string;
  activeModelContext: string;
  nextToolCall: string;
  retrievalState: string;
  memoryState: string;
  gateState: string;
  streamingState: string;
  costUsd: number;
  latencyNs: number;
  evidence: string;
  forkLabel: string;
  saveLabel: string;
}

export interface TraceScrubberModel {
  traceId: string;
  identity: TraceIdentity;
  totalNs: number;
  frames: TraceScrubberFrame[];
  unsupportedReason: string | null;
}

function valueText(value: TraceJsonValue | undefined): string {
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function payloadValue(payload: TracePayload | undefined, key: string): string {
  return valueText(payload?.[key]);
}

function payloadList(payload: TracePayload | undefined, key: string): string {
  const value = payload?.[key];
  if (!Array.isArray(value)) return valueText(value);
  return value
    .map((item) => valueText(item))
    .filter(Boolean)
    .join(", ");
}

function spanCost(span: Span): number {
  return span.cost?.total_usd ?? 0;
}

function contextFor(span: Span): string {
  if (span.category === "llm") {
    const model = valueText(span.attributes.model);
    const chunks = payloadList(span.input, "evidence_chunks");
    return `Model ${model || "unknown"} saw chunks ${chunks || "none recorded"}.`;
  }
  if (span.category === "retrieval") {
    const query = payloadValue(span.input, "query");
    return `Retrieval query: ${query || "not recorded"}.`;
  }
  if (span.category === "tool") {
    return `Tool input: ${JSON.stringify(span.input ?? {})}.`;
  }
  return `Context is at ${span.name}; inspect recorded inputs and outputs.`;
}

function retrievalFor(span: Span): string {
  if (span.category !== "retrieval") return "No retrieval frame active.";
  const chunks = span.normalized_payload?.chunks;
  if (!Array.isArray(chunks)) {
    return payloadValue(span.output, "top_chunk") || "No chunks recorded.";
  }
  return chunks
    .map((chunk, index) => {
      if (!chunk || typeof chunk !== "object" || Array.isArray(chunk)) {
        return "";
      }
      const id = valueText(chunk.id);
      const score = valueText(chunk.score);
      return `${index + 1}. ${id}${score ? ` (${score})` : ""}`;
    })
    .filter(Boolean)
    .join("; ");
}

function memoryFor(span: Span): string {
  if (span.category !== "memory") return "No memory write pending.";
  const before = payloadValue(span.input, "before") || "unknown";
  const after = payloadValue(span.output, "after") || "unknown";
  const policy = payloadValue(span.output, "policy") || "policy not recorded";
  return `${before} -> ${after}; ${policy}.`;
}

function gateFor(span: Span): string {
  if (span.category !== "budget" && span.category !== "policy") {
    return "No policy or budget gate active.";
  }
  return (
    payloadValue(span.output, "decision") ||
    payloadValue(span.normalized_payload, "decision") ||
    JSON.stringify(span.output ?? span.normalized_payload ?? {})
  );
}

function streamingFor(span: Span): string {
  if (span.category !== "llm") return "No streaming response in this frame.";
  const firstToken = span.events.find((event) => event.name === "first_token");
  const answer = payloadValue(span.output, "answer_summary");
  return firstToken
    ? `First token recorded; ${answer || "answer summary unavailable"}.`
    : answer || "LLM output recorded without token event.";
}

function nextToolFor(spans: Span[], frame: Span): string {
  if (frame.category === "tool") {
    return `${frame.name} is executing.`;
  }
  const next = spans.find(
    (span) => span.category === "tool" && span.start_ns >= frame.end_ns,
  );
  return next ? `${next.name} starts next.` : "No later tool call recorded.";
}

function identityFor(trace: Trace): TraceIdentity {
  return {
    traceId: trace.id,
    version: trace.summary?.deploy_version ?? "version not recorded",
    snapshotId: trace.summary?.snapshot_id ?? "snapshot not recorded",
    environment: trace.summary?.environment ?? "environment not recorded",
  };
}

export function buildTraceScrubberModel(trace: Trace): TraceScrubberModel {
  if (trace.spans.length === 0) {
    return {
      traceId: trace.id,
      identity: identityFor(trace),
      totalNs: 0,
      frames: [],
      unsupportedReason:
        "Trace has no spans, so the scrubber cannot derive frame state.",
    };
  }

  const spans = [...trace.spans].sort((a, b) => a.start_ns - b.start_ns);
  const startNs = Math.min(...spans.map((span) => span.start_ns));
  const endNs = Math.max(...spans.map((span) => span.end_ns));
  const totalNs = Math.max(1, endNs - startNs);

  const frames = spans.map<TraceScrubberFrame>((span, index) => {
    const atNs = span.end_ns;
    const costUsd = spans
      .filter((candidate) => candidate.end_ns <= atNs)
      .reduce((total, candidate) => total + spanCost(candidate), 0);
    return {
      id: `${trace.id}-${span.id}`,
      index,
      spanId: span.id,
      spanName: span.name,
      category: span.category,
      status: span.status,
      atNs,
      position: totalNs === 0 ? 0 : (atNs - startNs) / totalNs,
      label: `${index + 1}. ${span.name}`,
      activeModelContext: contextFor(span),
      nextToolCall: nextToolFor(spans, span),
      retrievalState: retrievalFor(span),
      memoryState: memoryFor(span),
      gateState: gateFor(span),
      streamingState: streamingFor(span),
      costUsd,
      latencyNs: atNs - startNs,
      evidence: `${span.id}: ${span.name} (${span.category}, ${span.status})`,
      forkLabel: `Fork from ${span.id}`,
      saveLabel: `Save ${span.id} as scene or eval seed`,
    };
  });

  return {
    traceId: trace.id,
    identity: identityFor(trace),
    totalNs,
    frames,
    unsupportedReason: null,
  };
}

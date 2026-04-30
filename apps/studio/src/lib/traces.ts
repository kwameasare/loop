/**
 * Trace types + fixture data.
 *
 * Real traces will be fetched from the data plane's tempo/jaeger
 * endpoint. For S0 we ship a small fixture so the studio renders
 * deterministically in tests and `pnpm dev`.
 */

export type SpanKind =
  | "server"
  | "client"
  | "internal"
  | "producer"
  | "consumer";

export type SpanEvent = {
  name: string;
  timestamp_ns: number;
  attributes?: Record<string, string | number | boolean>;
};

export type Span = {
  id: string;
  parent_id: string | null;
  name: string;
  kind: SpanKind;
  service: string;
  start_ns: number;
  end_ns: number;
  status: "ok" | "error" | "unset";
  attributes: Record<string, string | number | boolean>;
  events: SpanEvent[];
};

export type Trace = {
  id: string;
  spans: Span[];
};

export type LaidOutSpan = {
  span: Span;
  /** depth in the parent->child tree, 0 for the root. */
  depth: number;
  /** offset from the trace start, expressed as 0..1. */
  offset: number;
  /** width as a fraction of total trace duration, 0..1. */
  width: number;
};

export type TraceLayout = {
  trace: Trace;
  start_ns: number;
  end_ns: number;
  duration_ns: number;
  laidOut: LaidOutSpan[];
};

/**
 * Build a flat depth-ordered list with proportional offsets/widths.
 * Spans are sorted by start_ns within each parent so siblings render
 * in temporal order, and children always follow their parent.
 */
export function layoutTrace(trace: Trace): TraceLayout {
  if (trace.spans.length === 0) {
    return {
      trace,
      start_ns: 0,
      end_ns: 0,
      duration_ns: 0,
      laidOut: [],
    };
  }
  const startNs = Math.min(...trace.spans.map((s) => s.start_ns));
  const endNs = Math.max(...trace.spans.map((s) => s.end_ns));
  const duration = Math.max(1, endNs - startNs);

  // Index children by parent id.
  const childrenByParent = new Map<string | null, Span[]>();
  for (const span of trace.spans) {
    const arr = childrenByParent.get(span.parent_id) ?? [];
    arr.push(span);
    childrenByParent.set(span.parent_id, arr);
  }
  for (const arr of childrenByParent.values()) {
    arr.sort((a, b) => a.start_ns - b.start_ns);
  }

  const laidOut: LaidOutSpan[] = [];
  function walk(parentId: string | null, depth: number) {
    for (const span of childrenByParent.get(parentId) ?? []) {
      laidOut.push({
        span,
        depth,
        offset: (span.start_ns - startNs) / duration,
        width: Math.max(
          0.001,
          (span.end_ns - span.start_ns) / duration,
        ),
      });
      walk(span.id, depth + 1);
    }
  }
  walk(null, 0);

  return {
    trace,
    start_ns: startNs,
    end_ns: endNs,
    duration_ns: duration,
    laidOut,
  };
}

export function formatDurationNs(ns: number): string {
  if (ns < 1_000) return `${ns}ns`;
  if (ns < 1_000_000) return `${(ns / 1_000).toFixed(1)}µs`;
  if (ns < 1_000_000_000) return `${(ns / 1_000_000).toFixed(1)}ms`;
  return `${(ns / 1_000_000_000).toFixed(2)}s`;
}

const FIXTURE_TRACE: Trace = {
  id: "trc_demo_001",
  spans: [
    {
      id: "s1",
      parent_id: null,
      name: "POST /v1/agents/agt_support/turns",
      kind: "server",
      service: "runtime",
      start_ns: 0,
      end_ns: 850_000_000,
      status: "ok",
      attributes: { "http.method": "POST", "http.status_code": 200 },
      events: [],
    },
    {
      id: "s2",
      parent_id: "s1",
      name: "kb.retrieve",
      kind: "internal",
      service: "kb-engine",
      start_ns: 30_000_000,
      end_ns: 220_000_000,
      status: "ok",
      attributes: { top_k: 5, alpha: 0.5 },
      events: [{ name: "cache_miss", timestamp_ns: 35_000_000 }],
    },
    {
      id: "s3",
      parent_id: "s1",
      name: "llm.complete",
      kind: "client",
      service: "gateway",
      start_ns: 230_000_000,
      end_ns: 800_000_000,
      status: "ok",
      attributes: { model: "gpt-4o-mini", tokens_out: 142 },
      events: [],
    },
    {
      id: "s4",
      parent_id: "s3",
      name: "tool.search_docs",
      kind: "internal",
      service: "tool-host",
      start_ns: 400_000_000,
      end_ns: 520_000_000,
      status: "ok",
      attributes: { tool: "search_docs" },
      events: [],
    },
  ],
};

export async function getTrace(id: string): Promise<Trace | null> {
  if (id === FIXTURE_TRACE.id) return FIXTURE_TRACE;
  return null;
}

export const FIXTURE_TRACE_ID = FIXTURE_TRACE.id;

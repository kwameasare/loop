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

/** Lightweight row shown on the trace list page. */
export type TraceSummary = {
  id: string;
  agent_id: string;
  agent_name: string;
  root_name: string;
  status: "ok" | "error";
  duration_ns: number;
  started_at_ms: number;
  span_count: number;
};

export interface ListTracesOptions {
  /** Free-text search across id, root_name, agent_name (case-insensitive). */
  q?: string;
  status?: "ok" | "error" | "all";
  agent_id?: string;
  /** 1-based page index. Defaults to 1. */
  page?: number;
  /** Page size. Defaults to 20. */
  page_size?: number;
}

export interface ListTracesResult {
  traces: TraceSummary[];
  total: number;
  page: number;
  page_size: number;
  page_count: number;
}

const DAY_MS = 24 * 60 * 60 * 1000;
const TRACE_BASE_MS = Date.UTC(2026, 3, 30, 12, 0, 0);

/** Synthetic fixture set so the list page renders deterministically. */
export const FIXTURE_TRACES: TraceSummary[] = (() => {
  const agents: { id: string; name: string }[] = [
    { id: "agt_support", name: "Support Bot" },
    { id: "agt_sales", name: "Sales Concierge" },
    { id: "agt_ops", name: "Ops Assistant" },
  ];
  const rootNames = [
    "POST /v1/agents/{id}/turns",
    "POST /v1/agents/{id}/messages",
    "POST /v1/agents/{id}/tools/invoke",
    "POST /v1/agents/{id}/runs",
  ];
  const list: TraceSummary[] = [];
  for (let i = 0; i < 47; i += 1) {
    const agent = agents[i % agents.length];
    list.push({
      id: `trc_demo_${String(i + 1).padStart(3, "0")}`,
      agent_id: agent.id,
      agent_name: agent.name,
      root_name: rootNames[i % rootNames.length],
      status: i % 11 === 0 ? "error" : "ok",
      duration_ns: 100_000_000 + ((i * 37_000_000) % 1_500_000_000),
      started_at_ms: TRACE_BASE_MS - i * (DAY_MS / 12),
      span_count: 3 + (i % 8),
    });
  }
  list.unshift({
    id: FIXTURE_TRACE_ID,
    agent_id: "agt_support",
    agent_name: "Support Bot",
    root_name: "POST /v1/agents/agt_support/turns",
    status: "ok",
    duration_ns: 850_000_000,
    started_at_ms: TRACE_BASE_MS + 60 * 1000,
    span_count: FIXTURE_TRACE.spans.length,
  });
  return list;
})();

/**
 * Filter + paginate the in-memory trace fixture set. Real data will
 * come from the data plane; the contract here mirrors what that
 * endpoint should return so the UI can swap implementations cleanly.
 */
export function listTraces(
  records: readonly TraceSummary[],
  opts: ListTracesOptions = {},
): ListTracesResult {
  const page = Math.max(1, opts.page ?? 1);
  const page_size = Math.max(1, opts.page_size ?? 20);
  const status = opts.status ?? "all";
  const q = opts.q?.trim().toLowerCase() ?? "";

  const filtered = records.filter((t) => {
    if (status !== "all" && t.status !== status) return false;
    if (opts.agent_id && t.agent_id !== opts.agent_id) return false;
    if (q) {
      const hay = `${t.id} ${t.root_name} ${t.agent_name}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  filtered.sort((a, b) => b.started_at_ms - a.started_at_ms);

  const total = filtered.length;
  const page_count = Math.max(1, Math.ceil(total / page_size));
  const safePage = Math.min(page, page_count);
  const start = (safePage - 1) * page_size;
  return {
    traces: filtered.slice(start, start + page_size),
    total,
    page: safePage,
    page_size,
    page_count,
  };
}

export function formatTraceTimestamp(ms: number): string {
  const d = new Date(ms);
  const date = d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${date} ${hh}:${mm} UTC`;
}

import { targetUxFixtures } from "@/lib/target-ux";

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

export type TraceSpanCategory =
  | "llm"
  | "tool"
  | "retrieval"
  | "memory"
  | "channel"
  | "voice"
  | "sub_agent"
  | "retry"
  | "provider_failover"
  | "budget"
  | "policy"
  | "eval"
  | "deploy";

export type TraceJsonValue =
  | string
  | number
  | boolean
  | null
  | TraceJsonValue[]
  | { [key: string]: TraceJsonValue };

export type TracePayload = Record<string, TraceJsonValue>;

export type TraceRedaction = {
  field: string;
  reason: string;
  replacement: string;
  evidence: string;
};

export type TraceCostMath = {
  prompt_tokens: number;
  completion_tokens: number;
  input_usd: number;
  output_usd: number;
  tool_usd: number;
  total_usd: number;
  budget_source: string;
};

export type TraceRetry = {
  attempt: number;
  status: "ok" | "error" | "timeout";
  latency_ns: number;
  evidence: string;
};

export type TraceSpanLinks = {
  logs: string[];
  eval_cases: string[];
  migration_source?: string;
  deploy_version?: string;
};

export type Span = {
  id: string;
  parent_id: string | null;
  name: string;
  category: TraceSpanCategory;
  kind: SpanKind;
  service: string;
  start_ns: number;
  end_ns: number;
  status: "ok" | "error" | "unset";
  attributes: Record<string, string | number | boolean>;
  events: SpanEvent[];
  input?: TracePayload;
  output?: TracePayload;
  raw_payload?: TracePayload;
  normalized_payload?: TracePayload;
  redactions?: TraceRedaction[];
  cost?: TraceCostMath;
  retry_history?: TraceRetry[];
  links?: TraceSpanLinks;
};

export type TraceExplanation = {
  id: string;
  title: string;
  statement: string;
  evidence: string;
  source_span_id: string;
  confidence: number;
  confidence_level: "high" | "medium" | "low" | "unsupported";
};

export type TraceDetailSummary = {
  outcome: string;
  agent_name: string;
  environment: string;
  channel: string;
  provider: string;
  model: string;
  deploy_version: string;
  snapshot_id: string;
  total_latency_ns: number;
  total_cost_usd: number;
  tool_count: number;
  retrieval_count: number;
  memory_writes: number;
  eval_score: number | null;
  eval_suite: string | null;
};

export type Trace = {
  id: string;
  title?: string;
  summary?: TraceDetailSummary;
  explanations?: TraceExplanation[];
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
        width: Math.max(0.001, (span.end_ns - span.start_ns) / duration),
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

export function formatUsd(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 4,
    minimumFractionDigits: amount < 0.01 && amount > 0 ? 4 : 2,
    style: "currency",
  }).format(amount);
}

const NS_PER_MS = 1_000_000;

function ms(ms: number): number {
  return ms * NS_PER_MS;
}

function buildFixtureTrace(): Trace {
  const targetTrace = targetUxFixtures.traces[0]!;
  const agent =
    targetUxFixtures.agents.find((item) => item.id === targetTrace.agentId) ??
    targetUxFixtures.agents[0]!;
  const deploy =
    targetUxFixtures.deploys.find(
      (item) => item.agentId === targetTrace.agentId,
    ) ?? targetUxFixtures.deploys[0]!;
  const evalSuite = targetUxFixtures.evals[0]!;
  const targetContext = targetTrace.spans.find(
    (span) => span.id === "span_context",
  )!;
  const targetTool = targetTrace.spans.find((span) => span.id === "span_tool")!;
  const targetAnswer = targetTrace.spans.find(
    (span) => span.id === "span_answer",
  )!;

  const spans: Span[] = [
    {
      id: "span_turn",
      parent_id: null,
      name: "web.turn.accepted",
      category: "channel",
      kind: "server",
      service: "runtime",
      start_ns: ms(0),
      end_ns: ms(1_030),
      status: "ok",
      attributes: {
        channel: agent.channel,
        environment: targetUxFixtures.workspace.environment,
        trace_id: targetTrace.id,
      },
      events: [{ name: "turn_started", timestamp_ns: ms(0) }],
      input: {
        user_message: "I need to cancel my annual renewal before it bills.",
        channel: agent.channel,
      },
      output: {
        outcome: "answered with retention-policy handoff",
        trace_id: targetTrace.id,
      },
      raw_payload: {
        headers: {
          "x-loop-trace": targetTrace.id,
          authorization: "[redacted]",
        },
        body: {
          message: "I need to cancel my annual renewal before it bills.",
          customer_email: "j.morgan@example.com",
        },
      },
      normalized_payload: {
        turn_id: "turn_refund_742",
        message_text: "I need to cancel my annual renewal before it bills.",
        pii_fields: ["customer_email"],
      },
      redactions: [
        {
          field: "headers.authorization",
          reason: "credential",
          replacement: "[redacted]",
          evidence: "Gateway redaction policy pii_and_secret_v4",
        },
        {
          field: "body.customer_email",
          reason: "PII",
          replacement: "[email]",
          evidence: "Runtime PII classifier matched email pattern",
        },
      ],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0,
        total_usd: 0,
        budget_source: "workspace daily trace budget",
      },
      retry_history: [],
      links: {
        logs: ["runtime.turn.accepted trace_refund_742"],
        eval_cases: [evalSuite.id],
        deploy_version: targetTrace.version,
      },
    },
    {
      id: targetContext.id,
      parent_id: "span_turn",
      name: "kb.retrieve.refund_policy",
      category: "retrieval",
      kind: targetContext.kind,
      service: "kb-engine",
      start_ns: ms(targetContext.startedAtMs),
      end_ns: ms(targetContext.startedAtMs + targetContext.durationMs),
      status: targetContext.status,
      attributes: {
        top_k: 5,
        retrieved_chunks: 2,
        source: "refund_policy_2026.pdf",
      },
      events: [
        {
          name: "chunk_ranked",
          timestamp_ns: ms(targetContext.startedAtMs + 44),
          attributes: { chunk: "refund_policy_2026.pdf#p4", rank: 1 },
        },
      ],
      input: {
        query: "cancel annual renewal refund policy",
        filters: ["production", "refunds"],
      },
      output: {
        top_chunk: "refund_policy_2026.pdf#p4",
        second_chunk: "refund_policy_2024.pdf#p2",
        evidence: targetContext.evidence ?? "",
      },
      raw_payload: {
        qdrant_collection: "acme_support_knowledge",
        query_vector: "[768 floats omitted]",
      },
      normalized_payload: {
        chunks: [
          {
            id: "refund_policy_2026.pdf#p4",
            score: 0.91,
            quote: "Annual renewals can be cancelled before renewal capture.",
          },
          {
            id: "refund_policy_2024.pdf#p2",
            score: 0.78,
            quote: "Older renewal language, retained for migration parity.",
          },
        ],
      },
      redactions: [],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0.0016,
        total_usd: 0.0016,
        budget_source: "retrieval line item cost_tools",
      },
      retry_history: [],
      links: {
        logs: ["kb.retrieve trace_refund_742 span_context"],
        eval_cases: [evalSuite.id],
        migration_source: targetUxFixtures.migrations[0]!.id,
        deploy_version: targetTrace.version,
      },
    },
    {
      id: targetTool.id,
      parent_id: "span_turn",
      name: "tool.lookup_order",
      category: "tool",
      kind: targetTool.kind,
      service: "tool-host",
      start_ns: ms(targetTool.startedAtMs),
      end_ns: ms(targetTool.startedAtMs + targetTool.durationMs),
      status: targetTool.status,
      attributes: {
        tool: "lookup_order",
        side_effect: "read",
        authorization: "mcp",
      },
      events: [
        { name: "tool_result", timestamp_ns: ms(targetTool.startedAtMs + 238) },
      ],
      input: {
        order_id: "ord_renewal_431",
        fields: ["renewal_date", "plan", "payment_state"],
      },
      output: {
        renewal_date: "2026-05-09",
        payment_state: "not captured",
        plan: "annual",
      },
      raw_payload: {
        request_id: "tool_req_742",
        order_id: "ord_renewal_431",
      },
      normalized_payload: {
        entitlement_state: "cancelable_before_capture",
      },
      redactions: [],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0.004,
        total_usd: 0.004,
        budget_source: "tool-host meter",
      },
      retry_history: [],
      links: {
        logs: ["tool-host.lookup_order trace_refund_742 span_tool"],
        eval_cases: [evalSuite.id],
        deploy_version: targetTrace.version,
      },
    },
    {
      id: "span_budget",
      parent_id: "span_turn",
      name: "budget.check",
      category: "budget",
      kind: "internal",
      service: "gateway",
      start_ns: ms(383),
      end_ns: ms(405),
      status: "ok",
      attributes: {
        daily_budget_remaining_usd: 118.72,
        model_route: "quality",
      },
      events: [],
      input: {
        requested_model: "gpt-4.1-mini",
        estimated_tokens: 820,
      },
      output: {
        approved_model: "gpt-4.1-mini",
        budget_remaining_usd: 118.72,
      },
      raw_payload: {
        budget_id: "budget_support_daily",
        meter: "llm_tokens",
      },
      normalized_payload: {
        decision: "approved",
      },
      redactions: [],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0,
        total_usd: 0,
        budget_source: "workspace daily budget cap",
      },
      retry_history: [],
      links: {
        logs: ["gateway.budget.check trace_refund_742 span_budget"],
        eval_cases: [],
        deploy_version: targetTrace.version,
      },
    },
    {
      id: targetAnswer.id,
      parent_id: "span_turn",
      name: "llm.complete.grounded_answer",
      category: "llm",
      kind: targetAnswer.kind,
      service: "gateway",
      start_ns: ms(targetAnswer.startedAtMs),
      end_ns: ms(targetAnswer.startedAtMs + targetAnswer.durationMs),
      status: targetAnswer.status,
      attributes: {
        provider: "OpenAI",
        model: "gpt-4.1-mini",
        tokens_in: 812,
        tokens_out: 146,
      },
      events: [{ name: "first_token", timestamp_ns: ms(612) }],
      input: {
        model: "gpt-4.1-mini",
        evidence_chunks: [
          "refund_policy_2026.pdf#p4",
          "refund_policy_2024.pdf#p2",
        ],
        tool_results: ["lookup_order"],
      },
      output: {
        answer_summary:
          "Customer can cancel before renewal capture; handoff only if account owner confirmation fails.",
        grounded_source: "refund_policy_2026.pdf#p4",
      },
      raw_payload: {
        messages: [
          "system: Use policy citations when answering renewal questions.",
          "user: I need to cancel my annual renewal before it bills.",
        ],
      },
      normalized_payload: {
        citations: ["refund_policy_2026.pdf#p4"],
        tool_calls: [],
      },
      redactions: [],
      cost: {
        prompt_tokens: 812,
        completion_tokens: 146,
        input_usd: 0.0122,
        output_usd: 0.0254,
        tool_usd: 0,
        total_usd: 0.0376,
        budget_source: "llm reasoning line item cost_llm",
      },
      retry_history: [
        {
          attempt: 1,
          status: "ok",
          latency_ns: ms(targetAnswer.durationMs),
          evidence: "No provider retry recorded for span_answer",
        },
      ],
      links: {
        logs: ["gateway.llm.complete trace_refund_742 span_answer"],
        eval_cases: [evalSuite.id],
        deploy_version: targetTrace.version,
      },
    },
    {
      id: "span_memory",
      parent_id: "span_turn",
      name: "memory.write.preference",
      category: "memory",
      kind: "internal",
      service: "runtime",
      start_ns: ms(930),
      end_ns: ms(982),
      status: "ok",
      attributes: {
        memory_key: targetUxFixtures.memory[0]!.key,
        policy: targetUxFixtures.memory[0]!.policy,
      },
      events: [],
      input: {
        before: targetUxFixtures.memory[0]!.before,
        observed: targetUxFixtures.memory[0]!.source,
      },
      output: {
        after: targetUxFixtures.memory[0]!.after,
        policy: targetUxFixtures.memory[0]!.policy,
      },
      raw_payload: {
        memory_id: targetUxFixtures.memory[0]!.id,
        user_id: "usr_j_morgan",
      },
      normalized_payload: {
        key: targetUxFixtures.memory[0]!.key,
        value: targetUxFixtures.memory[0]!.after,
      },
      redactions: [],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0,
        total_usd: 0,
        budget_source: "included runtime memory write",
      },
      retry_history: [],
      links: {
        logs: ["runtime.memory.write trace_refund_742 span_memory"],
        eval_cases: [],
        deploy_version: targetTrace.version,
      },
    },
    {
      id: "span_eval",
      parent_id: "span_turn",
      name: "eval.attach.refund_parity",
      category: "eval",
      kind: "internal",
      service: "eval-harness",
      start_ns: ms(985),
      end_ns: ms(1_020),
      status: "ok",
      attributes: {
        suite: evalSuite.name,
        pass_rate: evalSuite.passRate,
        regression_count: evalSuite.regressionCount,
      },
      events: [],
      input: {
        trace_id: targetTrace.id,
        suite: evalSuite.id,
      },
      output: {
        pass_rate: evalSuite.passRate,
        regression_count: evalSuite.regressionCount,
      },
      raw_payload: {
        suite_id: evalSuite.id,
        case_ids: ["refund_window_basic", "refund_cancel_before_capture"],
      },
      normalized_payload: {
        deploy_gate: deploy.blockedReason ?? "ready",
      },
      redactions: [],
      cost: {
        prompt_tokens: 0,
        completion_tokens: 0,
        input_usd: 0,
        output_usd: 0,
        tool_usd: 0,
        total_usd: 0,
        budget_source: "eval metadata only",
      },
      retry_history: [],
      links: {
        logs: ["eval.attach trace_refund_742 span_eval"],
        eval_cases: [evalSuite.id, "refund_window_basic"],
        deploy_version: deploy.id,
      },
    },
  ];

  return {
    id: targetTrace.id,
    title: targetTrace.title,
    summary: {
      outcome: "Answered with grounded cancellation steps; no refund issued.",
      agent_name: agent.name,
      environment: targetUxFixtures.workspace.environment,
      channel: agent.channel,
      provider: "OpenAI",
      model: "gpt-4.1-mini",
      deploy_version: targetTrace.version,
      snapshot_id: targetTrace.snapshotId,
      total_latency_ns: ms(1_030),
      total_cost_usd: agent.costPerTurnUsd,
      tool_count: targetUxFixtures.tools.filter(
        (tool) => tool.id === "tool_lookup_order",
      ).length,
      retrieval_count: 2,
      memory_writes: targetUxFixtures.memory.length,
      eval_score: evalSuite.passRate,
      eval_suite: evalSuite.name,
    },
    explanations: [
      {
        id: "explain_policy_rank",
        title: "Answer grounded on the newer refund policy",
        statement:
          "The answer cites `refund_policy_2026.pdf` because span_context ranked it above `refund_policy_2024.pdf`.",
        evidence:
          targetContext.evidence ?? "span_context recorded the policy ranking.",
        source_span_id: targetContext.id,
        confidence: 82,
        confidence_level: "medium",
      },
      {
        id: "explain_cost",
        title: "Cost came mostly from the final model call",
        statement:
          "Cost is USD $0.043 because span_answer used 812 input tokens and 146 output tokens; lookup_order added USD $0.004.",
        evidence: "span_answer cost math plus span_tool tool meter",
        source_span_id: targetAnswer.id,
        confidence: 91,
        confidence_level: "high",
      },
      {
        id: "explain_unknown",
        title: "No evidence for private model reasoning",
        statement:
          "Unsupported. The trace does not expose private model reasoning; inspect inputs, outputs, retrieved chunks, and tool results instead.",
        evidence:
          "No hidden reasoning span or provider chain-of-thought is recorded.",
        source_span_id: targetAnswer.id,
        confidence: 0,
        confidence_level: "unsupported",
      },
    ],
    spans,
  };
}

const FIXTURE_TRACE: Trace = buildFixtureTrace();

export async function getTrace(id: string): Promise<Trace | null> {
  if (id === FIXTURE_TRACE.id) return FIXTURE_TRACE;
  return null;
}

/**
 * Fetch a single trace by turn id from cp.
 *
 * Blocked on cp-api PR: ``GET /v1/traces/{turn_id}`` is in the OpenAPI
 * spec but not yet routed in cp's app.py. Returns null on 404 so the
 * inspector renders the "trace not found" empty state cleanly.
 */
export async function fetchTraceByTurnId(
  turn_id: string,
  opts: TracesClientOptions = {},
): Promise<Trace | null> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const url = `${cpApiBaseUrl(opts.baseUrl)}/traces/${encodeURIComponent(turn_id)}`;
  const res = await fetcher(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`cp-api GET trace -> ${res.status}`);
  return (await res.json()) as Trace;
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

// ---------------------------------------------------------------- cp-api

export interface TracesClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for trace calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

interface CpTraceItem {
  workspace_id: string;
  trace_id: string;
  turn_id: string;
  conversation_id: string;
  agent_id: string;
  started_at: string;
  duration_ms: number;
  span_count: number;
  error: boolean;
}

export interface SearchTracesQuery {
  agent_id?: string;
  conversation_id?: string;
  turn_id?: string;
  started_at_from?: string;
  started_at_to?: string;
  only_errors?: boolean;
  page_size?: number;
  cursor?: string;
}

/**
 * Search persisted traces via ``GET /v1/workspaces/{id}/traces``.
 *
 * cp returns a sparser shape than the studio's ``TraceSummary`` —
 * agent_name and root_name aren't tracked at the cp layer yet, so we
 * fall back to the agent_id / a short trace label respectively. When
 * cp begins emitting display labels the mapper here is the only thing
 * that needs to update.
 */
export async function searchTraces(
  workspace_id: string,
  query: SearchTracesQuery = {},
  opts: TracesClientOptions = {},
): Promise<{ traces: TraceSummary[]; next_cursor: string | null }> {
  const fetcher = opts.fetcher ?? fetch;
  const headers: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  const params = new URLSearchParams();
  if (query.agent_id) params.set("agent_id", query.agent_id);
  if (query.conversation_id)
    params.set("conversation_id", query.conversation_id);
  if (query.turn_id) params.set("turn_id", query.turn_id);
  if (query.started_at_from)
    params.set("started_at_from", query.started_at_from);
  if (query.started_at_to) params.set("started_at_to", query.started_at_to);
  if (query.only_errors) params.set("only_errors", "true");
  if (query.page_size) params.set("page_size", String(query.page_size));
  if (query.cursor) params.set("cursor", query.cursor);
  const qs = params.toString();
  const url = `${cpApiBaseUrl(opts.baseUrl)}/workspaces/${encodeURIComponent(
    workspace_id,
  )}/traces${qs ? `?${qs}` : ""}`;
  const res = await fetcher(url, {
    method: "GET",
    headers,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`cp-api GET /traces -> ${res.status}`);
  const body = (await res.json()) as {
    items?: CpTraceItem[];
    next_cursor?: string | null;
  };
  return {
    traces: (body.items ?? []).map(toTraceSummary),
    next_cursor: body.next_cursor ?? null,
  };
}

function toTraceSummary(item: CpTraceItem): TraceSummary {
  return {
    id: item.trace_id,
    agent_id: item.agent_id,
    // cp doesn't store the human-readable agent name yet; the list
    // page falls back to the id so the row is still clickable.
    agent_name: item.agent_id,
    root_name: `turn ${item.turn_id.slice(0, 8)}`,
    status: item.error ? "error" : "ok",
    duration_ns: item.duration_ms * 1_000_000,
    started_at_ms: Date.parse(item.started_at),
    span_count: item.span_count,
  };
}

// ---------------------------------------------------------------- fixtures

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
    const agent = agents[i % agents.length] ?? {
      id: "agt_unknown",
      name: "Unknown Agent",
    };
    const root_name =
      rootNames[i % rootNames.length] ?? "POST /v1/agents/{id}/turns";
    list.push({
      id: `trc_demo_${String(i + 1).padStart(3, "0")}`,
      agent_id: agent.id,
      agent_name: agent.name,
      root_name,
      status: i % 11 === 0 ? "error" : "ok",
      duration_ns: 100_000_000 + ((i * 37_000_000) % 1_500_000_000),
      started_at_ms: TRACE_BASE_MS - i * (DAY_MS / 12),
      span_count: 3 + (i % 8),
    });
  }
  list.unshift({
    id: FIXTURE_TRACE_ID,
    agent_id: targetUxFixtures.workspace.activeAgentId,
    agent_name: FIXTURE_TRACE.summary?.agent_name ?? "Acme Support Concierge",
    root_name:
      FIXTURE_TRACE.title ?? "Customer asks to cancel an annual renewal",
    status: "ok",
    duration_ns: FIXTURE_TRACE.summary?.total_latency_ns ?? 850_000_000,
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

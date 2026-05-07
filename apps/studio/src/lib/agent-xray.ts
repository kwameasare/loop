import {
  fetchTraceByTurnId,
  getTrace,
  searchTraces,
  type Span,
  type Trace,
  type TracesClientOptions,
} from "@/lib/traces";

export type AgentXrayClaimKind =
  | "behavior"
  | "tool"
  | "retrieval"
  | "memory"
  | "cost"
  | "unsupported";

export interface AgentXrayClaim {
  id: string;
  kind: AgentXrayClaimKind;
  title: string;
  statement: string;
  metric: string;
  evidence: string;
  representativeTraceIds: string[];
  representativeSpanIds: string[];
  confidence: number;
}

export interface AgentXrayDeadWeightSummary {
  activeSections: string[];
  unusedSections: string[];
  sampledTurns: number;
  statement: string;
  evidence: string;
  representativeTraceIds: string[];
}

export interface AgentXrayModel {
  traceIds: string[];
  sampleSize: number;
  claims: AgentXrayClaim[];
  deadWeightSummary: AgentXrayDeadWeightSummary | null;
  unsupportedReason: string | null;
}

function spansByCategory(traces: Trace[], category: Span["category"]): Span[] {
  return traces.flatMap((trace) =>
    trace.spans.filter((span) => span.category === category),
  );
}

function tracesWithSpan(traces: Trace[], spanId: string): string[] {
  return traces
    .filter((trace) => trace.spans.some((span) => span.id === spanId))
    .map((trace) => trace.id);
}

function claimFromSpan(args: {
  id: string;
  kind: AgentXrayClaimKind;
  title: string;
  statement: string;
  metric: string;
  span: Span;
  traces: Trace[];
  confidence: number;
}): AgentXrayClaim {
  return {
    id: args.id,
    kind: args.kind,
    title: args.title,
    statement: args.statement,
    metric: args.metric,
    evidence: `${args.span.id}: ${args.span.name}`,
    representativeTraceIds: tracesWithSpan(args.traces, args.span.id),
    representativeSpanIds: [args.span.id],
    confidence: args.confidence,
  };
}

function parseSectionList(value: string | number | boolean | undefined): string[] {
  if (value === undefined) return [];
  return String(value)
    .split(/[,\n|]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildDeadWeightSummary(
  llm: Span | undefined,
  traceIds: string[],
): AgentXrayDeadWeightSummary | null {
  if (!llm) return null;
  const activeSections = parseSectionList(llm.attributes.used_prompt_sections);
  const allSections = parseSectionList(llm.attributes.all_prompt_sections);
  if (activeSections.length === 0 || allSections.length === 0) return null;
  const active = new Set(activeSections);
  const unusedSections = allSections.filter((section) => !active.has(section));
  if (unusedSections.length === 0) return null;
  const sampledTurns = Number(llm.attributes.sampled_turns ?? traceIds.length);
  const activeRatio = Math.round(
    (activeSections.length / Math.max(1, allSections.length)) * 100,
  );
  return {
    activeSections,
    unusedSections,
    sampledTurns,
    statement: `${activeRatio}% of prompt sections were visibly invoked in this sample; ${unusedSections.join(
      ", ",
    )} are dead weight until a representative trace proves otherwise.`,
    evidence: `${llm.id}: prompt-section telemetry`,
    representativeTraceIds: traceIds,
  };
}

export function buildAgentXrayModel(input: Trace | Trace[]): AgentXrayModel {
  const traces = Array.isArray(input) ? input : [input];
  const traceIds = traces.map((trace) => trace.id);
  const spans = traces.flatMap((trace) => trace.spans);
  if (spans.length === 0) {
    return {
      traceIds,
      sampleSize: 0,
      claims: [],
      deadWeightSummary: null,
      unsupportedReason:
        "Agent X-Ray needs recorded spans before it can make observed-behavior claims.",
    };
  }

  const claims: AgentXrayClaim[] = [];
  const retrieval = spansByCategory(traces, "retrieval")[0];
  const llm = spansByCategory(traces, "llm")[0];
  const tool = spansByCategory(traces, "tool")[0];
  const memory = spansByCategory(traces, "memory")[0];
  const deadWeightSummary = buildDeadWeightSummary(llm, traceIds);

  if (retrieval) {
    const source = String(retrieval.attributes.source ?? "source not recorded");
    const chunks = String(retrieval.attributes.retrieved_chunks ?? "unknown");
    claims.push(
      claimFromSpan({
        id: "xray-retrieval-policy",
        kind: "retrieval",
        title: "Refund policy retrieval influences the answer",
        statement: `${source} was retrieved with ${chunks} candidate chunks before the answer span.`,
        metric: `${chunks} chunks`,
        span: retrieval,
        traces,
        confidence: 82,
      }),
    );
  }

  if (tool) {
    const toolName = String(tool.attributes.tool ?? tool.name);
    claims.push(
      claimFromSpan({
        id: "xray-tool-lookup-order",
        kind: "tool",
        title: `${toolName} is visible in the production path`,
        statement: `${toolName} recorded input, output, auth mode, and side-effect evidence in this trace.`,
        metric: `${spansByCategory(traces, "tool").length} tool span`,
        span: tool,
        traces,
        confidence: 88,
      }),
    );
  }

  if (llm) {
    const tokensIn = Number(llm.attributes.tokens_in ?? 0);
    const tokensOut = Number(llm.attributes.tokens_out ?? 0);
    claims.push(
      claimFromSpan({
        id: "xray-cost-driver",
        kind: "cost",
        title: "Final answer span drives the visible token cost",
        statement: `${llm.name} recorded ${tokensIn} input tokens and ${tokensOut} output tokens.`,
        metric: `${
          llm.cost ? `$${llm.cost.total_usd.toFixed(4)}` : "cost not recorded"
        }`,
        span: llm,
        traces,
        confidence: llm.cost ? 91 : 54,
      }),
    );
  }

  if (memory) {
    claims.push(
      claimFromSpan({
        id: "xray-memory-write",
        kind: "memory",
        title: "Durable memory write is visible",
        statement: `${memory.name} recorded before/after state and policy evidence.`,
        metric: "1 memory write",
        span: memory,
        traces,
        confidence: 79,
      }),
    );
  }

  if (!deadWeightSummary) {
    claims.push({
      id: "xray-no-dead-prompt-claim",
      kind: "unsupported",
      title: "Prompt dead-code claim unsupported in this sample",
      statement:
        "This trace does not include prompt-section invocation telemetry, so X-Ray cannot claim that sections are unused.",
      metric: "unsupported",
      evidence: "No prompt-section spans or config reference were recorded.",
      representativeTraceIds: traceIds,
      representativeSpanIds: [],
      confidence: 0,
    });
  }

  return {
    traceIds,
    sampleSize: traces.length,
    claims,
    deadWeightSummary,
    unsupportedReason: null,
  };
}

export async function fetchAgentXrayTraces(
  workspaceId: string,
  opts: TracesClientOptions = {},
): Promise<Trace[]> {
  try {
    const result = await searchTraces(
      workspaceId,
      { page_size: 6 },
      opts,
    );
    const details = await Promise.all(
      result.traces.map((trace) =>
        fetchTraceByTurnId(trace.id, opts).catch(() => null),
      ),
    );
    return details.filter((trace): trace is Trace => trace !== null);
  } catch (err) {
    if (
      err instanceof Error &&
      /LOOP_CP_API_BASE_URL is required/.test(err.message)
    ) {
      const fallback = await getTrace("trace_refund_742");
      return fallback ? [fallback] : [];
    }
    throw err;
  }
}

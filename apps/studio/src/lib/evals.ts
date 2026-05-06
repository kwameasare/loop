import { targetUxFixtures } from "@/lib/target-ux";

/**
 * S253: Eval suites/runs helpers for the studio app.
 *
 * The cp-api eval endpoints expose:
 *   GET  /v1/evals/suites             → { items: EvalSuite[] }
 *   GET  /v1/evals/suites/{suite_id}  → EvalSuiteDetail (latest runs)
 *   GET  /v1/evals/runs/{run_id}      → EvalRunDetail (per-case results)
 *
 * If no cp-api base URL is configured we serve fixture data so the UX
 * can be reviewed end-to-end. Tests pin ``baseUrl`` to drive the live
 * fetch path.
 */

export type EvalCaseStatus = "pass" | "fail" | "error";
export type EvalRunStatus = "queued" | "running" | "completed" | "failed";
export type EvalCaseSource =
  | "manual"
  | "simulator"
  | "production"
  | "failed_turn"
  | "operator_resolution"
  | "migration_transcript"
  | "knowledge_source"
  | "policy_doc"
  | "generated_adversarial"
  | "support_macro";

export interface EvalSuite {
  id: string;
  name: string;
  agentId: string;
  cases: number;
  lastRunAt: string | null;
  passRate: number | null;
}

export interface EvalRunSummary {
  id: string;
  suiteId: string;
  status: EvalRunStatus;
  startedAt: string;
  finishedAt: string | null;
  passed: number;
  failed: number;
  errored: number;
  total: number;
  baselineRunId: string | null;
}

export interface EvalSuiteDetail extends EvalSuite {
  runs: EvalRunSummary[];
}

export interface EvalCaseResult {
  caseId: string;
  name: string;
  status: EvalCaseStatus;
  source?: EvalCaseSource;
  sourceRef?: string;
  expected: string;
  actual: string;
  beforeOutput?: string;
  afterOutput?: string;
  /** ``status`` of the same case in the baseline run, if known. */
  baselineStatus: EvalCaseStatus | null;
  durationMs: number;
  traceDiff?: string;
  toolDiff?: string;
  retrievalDiff?: string;
  memoryDiff?: string;
  costDeltaUsd?: number;
  latencyDeltaMs?: number;
  recommendedFix?: string;
  evidence?: string;
}

export interface EvalRunDetail extends EvalRunSummary {
  cases: EvalCaseResult[];
}

export interface EvalDiffEntry {
  caseId: string;
  name: string;
  current: EvalCaseStatus;
  baseline: EvalCaseStatus | null;
  /** ``regression`` = pass→fail/error; ``recovered`` = fail→pass; ``stable`` otherwise. */
  kind: "regression" | "recovered" | "stable" | "new";
}

export interface EvalsHelperOptions {
  fetcher?: typeof fetch;
  baseUrl?: string;
  token?: string;
}

export interface EvalCreationSource {
  id: string;
  source: EvalCaseSource;
  label: string;
  count: number;
  evidence: string;
  provenance: string;
  actionLabel: string;
  confidence: "high" | "medium" | "low" | "unsupported";
}

export interface EvalScorerConfig {
  id: string;
  label: string;
  threshold: string;
  evidence: string;
}

export interface EvalSuiteBuilderView {
  suiteId: string;
  intent: string;
  owner: string;
  requiredDeployGate: string;
  scorers: EvalScorerConfig[];
  datasets: string[];
  fixtures: string[];
  cassettes: string[];
  thresholds: string[];
  historicalTrend: string;
  flakyCaseDetection: string;
  costBudgetUsd: number;
  latencyBudgetMs: number;
}

export interface EvalResultDiffView {
  runId: string;
  caseId: string;
  caseName: string;
  status: EvalCaseStatus;
  beforeOutput: string;
  afterOutput: string;
  traceDiff: string;
  toolDiff: string;
  retrievalDiff: string;
  memoryDiff: string;
  costDeltaUsd: number;
  latencyDeltaMs: number;
  recommendedFix: string;
  evidence: string;
}

export interface EvalFoundryModel {
  creationSources: EvalCreationSource[];
  suiteBuilders: EvalSuiteBuilderView[];
  featuredResult: EvalResultDiffView | null;
}

function resolveBase(opts: EvalsHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? (process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL)
      : undefined);
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function authHeaders(opts: EvalsHelperOptions): Record<string, string> {
  const headers: Record<string, string> = { accept: "application/json" };
  if (opts.token) headers.authorization = `Bearer ${opts.token}`;
  return headers;
}

const FIXTURE_SUITES: EvalSuite[] = [
  {
    id: "evs_support_smoke",
    name: targetUxFixtures.evals[0]?.name ?? "support smoke",
    agentId: targetUxFixtures.workspace.activeAgentId,
    cases: 18,
    lastRunAt: targetUxFixtures.evals[0]?.lastRun ?? "2026-05-06T08:30:00Z",
    passRate: (targetUxFixtures.evals[0]?.passRate ?? 96) / 100,
  },
  {
    id: "evs_routing_regression",
    name: "routing regression",
    agentId: targetUxFixtures.workspace.activeAgentId,
    cases: 24,
    lastRunAt: "2026-05-05T17:04:55Z",
    passRate: 0.875,
  },
];

const CREATION_SOURCES: EvalCreationSource[] = [
  {
    id: "src_manual_refund",
    source: "manual",
    label: "Manual case",
    count: 1,
    evidence: "Builder-authored refund-window case",
    provenance: "Explicit manual author: eval author",
    actionLabel: "Add manual case",
    confidence: "high",
  },
  {
    id: "src_simulator_refund",
    source: "simulator",
    label: "Simulator run",
    count: 6,
    evidence: "Last simulator session covered cancellation paraphrases",
    provenance: "Simulator transcript set sim_refund_may_06",
    actionLabel: "Save simulator turns",
    confidence: "medium",
  },
  {
    id: "src_production_replay",
    source: "production",
    label: "Production conversations",
    count: 12,
    evidence: `${targetUxFixtures.traces[0]!.id} and 11 related refund turns`,
    provenance: "Production replay sample, 2026-05-06 UTC",
    actionLabel: "Save production turns",
    confidence: "high",
  },
  {
    id: "src_failed_turn",
    source: "failed_turn",
    label: "Failed turns",
    count: 3,
    evidence: "Refund-window failures had unresolved policy conflict",
    provenance: "Failed eval and trace status evidence",
    actionLabel: "Create regression cases",
    confidence: "high",
  },
  {
    id: "src_operator_resolution",
    source: "operator_resolution",
    label: "Operator resolutions",
    count: 4,
    evidence:
      "Operators escalated legal-threat cancellations with policy notes",
    provenance: "HITL resolution notes linked to trace_refund_742",
    actionLabel: "Use resolutions",
    confidence: "medium",
  },
  {
    id: "src_migration_transcript",
    source: "migration_transcript",
    label: "Migration transcripts",
    count: 9,
    evidence: `${targetUxFixtures.migrations[0]!.id} parity transcript sample`,
    provenance: "Botpress import lineage snapshot",
    actionLabel: "Use migration transcript",
    confidence: "medium",
  },
  {
    id: "src_kb_policy",
    source: "knowledge_source",
    label: "KB and policy docs",
    count: 7,
    evidence: "refund_policy_2026.pdf is cited by the trace and result diff",
    provenance: "Knowledge source chunk refund_policy_2026.pdf#p4",
    actionLabel: "Generate from KB",
    confidence: "medium",
  },
  {
    id: "src_generated_adversarial",
    source: "generated_adversarial",
    label: "Generated adversarial",
    count: 5,
    evidence:
      "Synthetic cancellation paraphrases seeded from production traces",
    provenance:
      "Synthetic provenance: trace_refund_742 + refund_policy_2026.pdf",
    actionLabel: "Review generated cases",
    confidence: "low",
  },
  {
    id: "src_support_macros",
    source: "support_macro",
    label: "Support macros",
    count: 0,
    evidence: "No support macro import is connected",
    provenance: "Unsupported until a helpdesk source is connected",
    actionLabel: "Connect macro source",
    confidence: "unsupported",
  },
];

const SUITE_BUILDERS: Record<string, EvalSuiteBuilderView> = {
  evs_support_smoke: {
    suiteId: "evs_support_smoke",
    intent: "Prevent refund and cancellation regressions before canary.",
    owner: "Support Automation",
    requiredDeployGate: "Canary promotion requires pass rate >= 95%",
    scorers: [
      {
        id: "grounded_answer",
        label: "Grounded answer",
        threshold: ">= 0.90",
        evidence: "Checks citation to refund_policy_2026.pdf#p4",
      },
      {
        id: "tool_call_assert",
        label: "Tool call assertion",
        threshold: "lookup_order before final answer",
        evidence: "Trace span span_tool must precede span_answer",
      },
      {
        id: "cost_le",
        label: "Cost <= USD $0.05",
        threshold: "<= 0.05 per turn",
        evidence: "Cost line items from trace theater",
      },
    ],
    datasets: ["production_refunds_may_06", "botpress_parity_refunds"],
    fixtures: [
      targetUxFixtures.traces[0]!.id,
      targetUxFixtures.scenes[0]!.id,
      "refund_policy_2026.pdf#p4",
    ],
    cassettes: ["cassette_refund_lookup_order_v23"],
    thresholds: ["Pass rate >= 95%", "No PII leak", "p95 latency <= 1.2s"],
    historicalTrend: "96% pass rate, one Spanish paraphrase regression",
    flakyCaseDetection: "0 flaky cases in the last 5 runs",
    costBudgetUsd: 0.05,
    latencyBudgetMs: 1_200,
  },
  evs_routing_regression: {
    suiteId: "evs_routing_regression",
    intent: "Keep escalation routing stable while policy language changes.",
    owner: "Operator Experience",
    requiredDeployGate: "Staging deploy warns below 90%",
    scorers: [
      {
        id: "handoff_route",
        label: "Handoff route",
        threshold: "legal threat -> retention owner",
        evidence: "Operator resolution labels",
      },
      {
        id: "latency_le",
        label: "Latency <= 1.5s",
        threshold: "<= 1,500 ms",
        evidence: "Replay latency budget",
      },
    ],
    datasets: ["operator_resolution_refunds", "migration_legal_threats"],
    fixtures: [
      targetUxFixtures.inbox[0]!.traceId,
      targetUxFixtures.scenes[0]!.id,
    ],
    cassettes: ["cassette_operator_handoff_v7"],
    thresholds: ["No critical route regressions", "p95 latency <= 1.5s"],
    historicalTrend: "87.5% pass rate, routing drift under review",
    flakyCaseDetection: "1 flaky Teams handoff case quarantined",
    costBudgetUsd: 0.06,
    latencyBudgetMs: 1_500,
  },
};

function fixtureSuiteDetail(suiteId: string): EvalSuiteDetail | null {
  const suite = FIXTURE_SUITES.find((s) => s.id === suiteId);
  if (!suite) return null;
  const runs: EvalRunSummary[] = [
    {
      id: `evr_${suiteId}_002`,
      suiteId,
      status: "completed",
      startedAt: "2025-02-20T18:30:00Z",
      finishedAt: "2025-02-20T18:31:02Z",
      passed: 11,
      failed: 1,
      errored: 0,
      total: 12,
      baselineRunId: `evr_${suiteId}_001`,
    },
    {
      id: `evr_${suiteId}_001`,
      suiteId,
      status: "completed",
      startedAt: "2025-02-19T18:30:00Z",
      finishedAt: "2025-02-19T18:30:58Z",
      passed: 12,
      failed: 0,
      errored: 0,
      total: 12,
      baselineRunId: null,
    },
  ];
  return { ...suite, runs };
}

function fixtureRunDetail(runId: string): EvalRunDetail | null {
  if (!runId.startsWith("evr_")) return null;
  // Strip the "evr_" prefix and the trailing "_NNN" run number to recover
  // the suite id (e.g. ``evr_evs_support_smoke_002`` → ``evs_support_smoke``).
  const withoutPrefix = runId.slice("evr_".length);
  const suiteId = withoutPrefix.replace(/_\d+$/, "");
  const summary = fixtureSuiteDetail(suiteId)?.runs.find((r) => r.id === runId);
  if (!summary) return null;
  const cases: EvalCaseResult[] = [
    {
      caseId: "c1",
      name: "greets new user",
      status: "pass",
      source: "manual",
      sourceRef: "manual:greets_new_user",
      expected: "Hello! How can I help?",
      actual: "Hello! How can I help?",
      beforeOutput: "Hello! How can I help?",
      afterOutput: "Hello! How can I help?",
      baselineStatus: "pass",
      durationMs: 412,
      traceDiff: "No trace diff.",
      toolDiff: "No tool calls expected.",
      retrievalDiff: "No retrieval expected.",
      memoryDiff: "No memory writes.",
      costDeltaUsd: 0,
      latencyDeltaMs: 4,
      recommendedFix: "No fix needed.",
      evidence: "Manual smoke case stayed stable.",
    },
    {
      caseId: "c2",
      name: "routes refund to billing",
      status: summary.failed > 0 ? "fail" : "pass",
      source: "production",
      sourceRef: targetUxFixtures.traces[0]!.id,
      expected: "transfer to billing",
      actual: summary.failed > 0 ? "answered directly" : "transfer to billing",
      beforeOutput: "transfer to billing",
      afterOutput:
        summary.failed > 0 ? "answered directly" : "transfer to billing",
      baselineStatus: "pass",
      durationMs: 689,
      traceDiff: "span_answer skipped the retention handoff branch.",
      toolDiff: "lookup_order still ran before final answer.",
      retrievalDiff:
        "refund_policy_2026.pdf ranked first, but the answer omitted escalation wording.",
      memoryDiff: "No durable memory change.",
      costDeltaUsd: 0.0042,
      latencyDeltaMs: 118,
      recommendedFix:
        "Add a routing assertion for annual renewals before answering directly.",
      evidence: "trace_refund_742, refund_policy_2026.pdf#p4, eval_refunds",
    },
    {
      caseId: "c3",
      name: "declines unsafe request",
      status: "pass",
      source: "generated_adversarial",
      sourceRef: "synthetic:unsafe_refund_abuse",
      expected: "refusal",
      actual: "refusal",
      beforeOutput: "refusal",
      afterOutput: "refusal",
      baselineStatus: "pass",
      durationMs: 305,
      traceDiff: "Policy span remained stable.",
      toolDiff: "No money-movement tool call.",
      retrievalDiff: "No retrieval needed.",
      memoryDiff: "No memory writes.",
      costDeltaUsd: -0.001,
      latencyDeltaMs: -22,
      recommendedFix: "Keep policy scorer attached to deploy gate.",
      evidence: "Synthetic case generated from unsafe refund abuse policy.",
    },
  ];
  return { ...summary, cases };
}

export async function listEvalSuites(
  opts: EvalsHelperOptions = {},
): Promise<{ items: EvalSuite[] }> {
  const base = resolveBase(opts);
  if (!base) return { items: FIXTURE_SUITES };
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/evals/suites`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (!res.ok) throw new Error(`listEvalSuites failed: ${res.status}`);
  return (await res.json()) as { items: EvalSuite[] };
}

export async function getEvalSuite(
  suiteId: string,
  opts: EvalsHelperOptions = {},
): Promise<EvalSuiteDetail | null> {
  const base = resolveBase(opts);
  if (!base) return fixtureSuiteDetail(suiteId);
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/evals/suites/${suiteId}`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`getEvalSuite failed: ${res.status}`);
  return (await res.json()) as EvalSuiteDetail;
}

export async function getEvalRun(
  runId: string,
  opts: EvalsHelperOptions = {},
): Promise<EvalRunDetail | null> {
  const base = resolveBase(opts);
  if (!base) return fixtureRunDetail(runId);
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/evals/runs/${runId}`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`getEvalRun failed: ${res.status}`);
  return (await res.json()) as EvalRunDetail;
}

export function diffAgainstBaseline(
  current: EvalRunDetail,
  baseline: EvalRunDetail | null,
): EvalDiffEntry[] {
  const baselineMap = new Map<string, EvalCaseResult>();
  if (baseline) {
    for (const c of baseline.cases) baselineMap.set(c.caseId, c);
  }
  return current.cases.map((c) => {
    const prev = baselineMap.get(c.caseId);
    if (!prev) {
      return {
        caseId: c.caseId,
        name: c.name,
        current: c.status,
        baseline: null,
        kind: "new",
      };
    }
    let kind: EvalDiffEntry["kind"] = "stable";
    if (prev.status === "pass" && c.status !== "pass") kind = "regression";
    else if (prev.status !== "pass" && c.status === "pass") kind = "recovered";
    return {
      caseId: c.caseId,
      name: c.name,
      current: c.status,
      baseline: prev.status,
      kind,
    };
  });
}

export function resultDiffForRun(
  run: EvalRunDetail,
): EvalResultDiffView | null {
  const caseWithDiff =
    run.cases.find((item) => item.status !== "pass" && item.beforeOutput) ??
    run.cases.find((item) => item.beforeOutput);
  if (!caseWithDiff) return null;
  return {
    runId: run.id,
    caseId: caseWithDiff.caseId,
    caseName: caseWithDiff.name,
    status: caseWithDiff.status,
    beforeOutput: caseWithDiff.beforeOutput ?? caseWithDiff.expected,
    afterOutput: caseWithDiff.afterOutput ?? caseWithDiff.actual,
    traceDiff: caseWithDiff.traceDiff ?? "No trace diff recorded.",
    toolDiff: caseWithDiff.toolDiff ?? "No tool diff recorded.",
    retrievalDiff: caseWithDiff.retrievalDiff ?? "No retrieval diff recorded.",
    memoryDiff: caseWithDiff.memoryDiff ?? "No memory diff recorded.",
    costDeltaUsd: caseWithDiff.costDeltaUsd ?? 0,
    latencyDeltaMs: caseWithDiff.latencyDeltaMs ?? 0,
    recommendedFix:
      caseWithDiff.recommendedFix ??
      "Open the trace and add evidence before changing behavior.",
    evidence: caseWithDiff.evidence ?? "No evidence attached.",
  };
}

export function getEvalFoundryModel(
  suites: readonly EvalSuite[] = FIXTURE_SUITES,
): EvalFoundryModel {
  const suiteBuilders = suites.map((suite) => {
    const known = SUITE_BUILDERS[suite.id];
    if (known) return known;
    return {
      suiteId: suite.id,
      intent: "Measure behavior before deploy.",
      owner: "Eval author",
      requiredDeployGate: "Not attached to deploy gate yet",
      scorers: [
        {
          id: "accuracy",
          label: "Accuracy",
          threshold: ">= 0.85",
          evidence: "Default scorer until suite config loads",
        },
      ],
      datasets: [suite.name],
      fixtures: [],
      cassettes: [],
      thresholds: ["Pass rate >= 85%"],
      historicalTrend: "No historical trend yet",
      flakyCaseDetection: "No flaky cases detected",
      costBudgetUsd: 0.05,
      latencyBudgetMs: 1_500,
    };
  });
  const featuredRun = fixtureRunDetail("evr_evs_support_smoke_002");
  return {
    creationSources: CREATION_SOURCES,
    suiteBuilders,
    featuredResult: featuredRun ? resultDiffForRun(featuredRun) : null,
  };
}

export function formatPassRate(rate: number | null): string {
  if (rate === null) return "—";
  return `${Math.round(rate * 1000) / 10}%`;
}

export function formatEvalUsd(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 4,
    minimumFractionDigits: amount !== 0 && Math.abs(amount) < 0.01 ? 4 : 2,
    signDisplay: amount === 0 ? "auto" : "always",
    style: "currency",
  }).format(amount);
}

// ---------------------------------------------------------------- create

export interface CreateEvalSuiteInput {
  name: string;
  dataset_ref: string;
  metrics: string[];
}

/**
 * POST a new eval suite to ``/v1/eval-suites``. Returns the created
 * suite summary so the page can refresh in place. Throws on non-2xx
 * so the form can surface the cp-side validation message.
 */
export async function createEvalSuite(
  input: CreateEvalSuiteInput,
  opts: EvalsHelperOptions = {},
): Promise<EvalSuite> {
  const base = resolveBase(opts);
  if (!base) {
    // The fixture mode used in dev/tests can't really create rows;
    // we return an in-memory shape so the form smoke-passes.
    return {
      id: `evs_${Math.random().toString(36).slice(2, 10)}`,
      name: input.name,
      agentId: "",
      cases: 0,
      lastRunAt: null,
      passRate: null,
    };
  }
  const fetcher = opts.fetcher ?? fetch;
  const headers = {
    ...authHeaders(opts),
    "content-type": "application/json",
  };
  const res = await fetcher(`${base}/eval-suites`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      name: input.name,
      dataset_ref: input.dataset_ref,
      metrics: input.metrics,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`createEvalSuite failed: ${res.status}`);
  }
  const body = (await res.json()) as Partial<EvalSuite> & {
    id?: string;
    name?: string;
  };
  return {
    id: body.id ?? "",
    name: body.name ?? input.name,
    agentId: body.agentId ?? "",
    cases: body.cases ?? 0,
    lastRunAt: body.lastRunAt ?? null,
    passRate: body.passRate ?? null,
  };
}

export interface TriggerEvalSuiteRunResult {
  id: string;
}

/**
 * Trigger a new eval run for a suite.
 */
export async function triggerEvalSuiteRun(
  suiteId: string,
  opts: EvalsHelperOptions = {},
): Promise<TriggerEvalSuiteRunResult> {
  const base = resolveBase(opts);
  if (!base) {
    return { id: `evr_${Math.random().toString(36).slice(2, 10)}` };
  }
  const fetcher = opts.fetcher ?? fetch;
  const headers = {
    ...authHeaders(opts),
    "content-type": "application/json",
  };
  const res = await fetcher(
    `${base}/eval-suites/${encodeURIComponent(suiteId)}/runs`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({}),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(`triggerEvalSuiteRun failed: ${res.status}`);
  }
  const body = (await res.json()) as { id?: string };
  if (!body.id) {
    throw new Error("triggerEvalSuiteRun failed: missing run id");
  }
  return { id: body.id };
}

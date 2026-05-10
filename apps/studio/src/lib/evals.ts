/**
 * S253: Eval suites/runs helpers for the studio app.
 *
 * The cp-api eval endpoints expose:
 *   GET  /v1/workspaces/{workspace_id}/eval-suites → { items: EvalSuite[] }
 *   POST /v1/workspaces/{workspace_id}/eval-suites → EvalSuite
 *   GET  /v1/eval-suites/{suite_id}                → EvalSuiteDetail
 *   GET  /v1/eval-runs/{run_id}                    → EvalRunDetail
 *
 * Fixture data is available only for explicit demo/test callers. Route-facing
 * code must surface a degraded state when the cp-api is not configured.
 */

export type EvalCaseStatus = "pass" | "fail" | "error";
export type EvalRunStatus = "queued" | "running" | "completed" | "failed";
export type EvalCaseSource =
  | "manual"
  | "production_conversation"
  | "simulator_run"
  | "human_handoff"
  | "reviewer_comment"
  | "migration_parity_gap"
  | "adversarial_catch"
  | "incident_cluster"
  | "failed_turn"
  | "knowledge_source"
  | "policy_doc"
  | "support_macro"
  | "simulator"
  | "production"
  | "operator_resolution"
  | "migration_transcript"
  | "generated_adversarial";

const FIXTURE_AGENT_ID = "fixture_agent_support";
const FIXTURE_TRACE_ID = "fixture_trace_refund_742";
const FIXTURE_SCENE_ID = "fixture_scene_escalation_legal_threat";
const FIXTURE_MIGRATION_ID = "fixture_migration_botpress_may";
const FIXTURE_INBOX_TRACE_ID = "fixture_trace_handoff_legal_threat";
const FIXTURE_PROVENANCE =
  "Fixture mode: deterministic local-dev eval evidence, not live production data.";
export const EVAL_SUITES_CP_API_REQUIRED =
  "LOOP_CP_API_BASE_URL is required to load eval suites.";
export const EVAL_SUITE_DETAIL_CP_API_REQUIRED =
  "LOOP_CP_API_BASE_URL is required to load eval suite details.";
export const EVAL_RUN_DETAIL_CP_API_REQUIRED =
  "LOOP_CP_API_BASE_URL is required to load eval run details.";

export interface EvalSuite {
  id: string;
  name: string;
  agentId: string;
  cases: number;
  lastRunAt: string | null;
  passRate: number | null;
  creationSources?: EvalCreationSource[];
  provenanceCases?: EvalProvenanceCase[];
  changePackageLinks?: EvalChangePackageLink[];
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
  allowFixture?: boolean;
  workspaceId?: string | null | undefined;
}

export interface EvalSuiteListResponse {
  items: EvalSuite[];
  degraded_reason?: string | undefined;
  evidence_mode?: "live" | "fixture" | "degraded" | undefined;
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

export interface EvalProvenanceCase {
  id: string;
  agentId: string;
  suiteId: string;
  sourceType: EvalCaseSource;
  sourceRef: string;
  input: string;
  expectedBehavior: string;
  channelType: string;
  riskTags: string[];
  status: "candidate" | "active" | "quarantined" | "retired";
  changePackageRef: string | null;
  evidence: string;
}

export interface EvalChangePackageLink {
  id: string;
  changePackageRef: string;
  evalResultsRef: string;
  suiteId: string;
  gate: string;
  status: "ready" | "blocked" | "missing" | "stale";
  evidence: string;
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
  provenanceCases: EvalProvenanceCase[];
  changePackageLinks: EvalChangePackageLink[];
}

export interface EvalFoundryModelOptions {
  evidenceMode?: "live" | "fixture" | "degraded";
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

type CpEvalSuite = Partial<{
  id: string;
  workspace_id: string;
  name: string;
  dataset_ref: string;
  metrics: string[];
  agent_id: string | null;
  agentId: string;
  cases: number;
  case_count: number;
  last_run_at: string | null;
  lastRunAt: string | null;
  pass_rate: number | null;
  passRate: number | null;
  runs: CpEvalRun[];
}>;

type CpEvalRun = Partial<{
  id: string;
  suite_id: string;
  suiteId: string;
  state: string;
  status: string;
  started_at: string;
  startedAt: string;
  completed_at: string | null;
  finishedAt: string | null;
  passed: number;
  failed: number;
  errored: number;
  total: number;
  baseline_run_id: string | null;
  baselineRunId: string | null;
  cases: CpEvalCaseResult[];
}>;

type CpEvalCaseResult = Partial<{
  case_id: string;
  caseId: string;
  name: string;
  status: EvalCaseStatus;
  source: EvalCaseSource;
  source_ref: string;
  sourceRef: string;
  expected: unknown;
  actual: unknown;
  baseline_status: EvalCaseStatus | null;
  baselineStatus: EvalCaseStatus | null;
  duration_ms: number;
  durationMs: number;
}>;

function agentIdFromDatasetRef(ref: string | undefined): string {
  if (!ref?.startsWith("agent:")) return "";
  const [, agentId] = ref.split(":");
  return agentId ?? "";
}

function stringifyEvidence(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function mapEvalSuite(raw: CpEvalSuite): EvalSuite {
  const datasetRef = raw.dataset_ref;
  return {
    id: raw.id ?? "",
    name: raw.name ?? "Untitled eval suite",
    agentId: raw.agent_id ?? raw.agentId ?? agentIdFromDatasetRef(datasetRef),
    cases: raw.cases ?? raw.case_count ?? 0,
    lastRunAt: raw.last_run_at ?? raw.lastRunAt ?? null,
    passRate: raw.pass_rate ?? raw.passRate ?? null,
  };
}

function mapEvalRun(raw: CpEvalRun, fallbackSuiteId = ""): EvalRunSummary {
  const status = raw.status ?? raw.state ?? "queued";
  return {
    id: raw.id ?? "",
    suiteId: raw.suite_id ?? raw.suiteId ?? fallbackSuiteId,
    status: status === "pending" ? "queued" : (status as EvalRunStatus),
    startedAt: raw.started_at ?? raw.startedAt ?? "",
    finishedAt: raw.completed_at ?? raw.finishedAt ?? null,
    passed: raw.passed ?? 0,
    failed: raw.failed ?? 0,
    errored: raw.errored ?? 0,
    total: raw.total ?? 0,
    baselineRunId: raw.baseline_run_id ?? raw.baselineRunId ?? null,
  };
}

function mapEvalCaseResult(raw: CpEvalCaseResult): EvalCaseResult {
  const sourceRef = raw.source_ref ?? raw.sourceRef;
  return {
    caseId: raw.case_id ?? raw.caseId ?? "",
    name: raw.name ?? "Untitled eval case",
    status: raw.status ?? "pass",
    ...(raw.source ? { source: raw.source } : {}),
    ...(sourceRef ? { sourceRef } : {}),
    expected: stringifyEvidence(raw.expected),
    actual: stringifyEvidence(raw.actual),
    baselineStatus: raw.baseline_status ?? raw.baselineStatus ?? null,
    durationMs: raw.duration_ms ?? raw.durationMs ?? 0,
  };
}

const FIXTURE_SUITES: EvalSuite[] = [
  {
    id: "evs_support_smoke",
    name: "fixture support smoke",
    agentId: FIXTURE_AGENT_ID,
    cases: 18,
    lastRunAt: "2026-05-06T08:30:00Z",
    passRate: 0.96,
  },
  {
    id: "evs_routing_regression",
    name: "fixture routing regression",
    agentId: FIXTURE_AGENT_ID,
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
    source: "simulator_run",
    label: "Simulator run",
    count: 6,
    evidence: "Last simulator session covered cancellation paraphrases",
    provenance: "Simulator transcript set sim_refund_may_06",
    actionLabel: "Save simulator turns",
    confidence: "medium",
  },
  {
    id: "src_production_replay",
    source: "production_conversation",
    label: "Production conversations",
    count: 12,
    evidence: `${FIXTURE_TRACE_ID} and 11 related fixture refund turns`,
    provenance: FIXTURE_PROVENANCE,
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
    source: "human_handoff",
    label: "Operator resolutions",
    count: 4,
    evidence:
      "Operators escalated legal-threat cancellations with policy notes",
    provenance: `${FIXTURE_PROVENANCE} Handoff notes are linked to ${FIXTURE_INBOX_TRACE_ID}.`,
    actionLabel: "Use resolutions",
    confidence: "medium",
  },
  {
    id: "src_reviewer_comment",
    source: "reviewer_comment",
    label: "Reviewer comments",
    count: 2,
    evidence:
      "Resolved review comments specify expected behavior for refund exceptions",
    provenance: `${FIXTURE_PROVENANCE} Comment thread th_refund_exception_review.`,
    actionLabel: "Convert comments",
    confidence: "medium",
  },
  {
    id: "src_migration_transcript",
    source: "migration_parity_gap",
    label: "Migration parity gaps",
    count: 9,
    evidence: `${FIXTURE_MIGRATION_ID} parity transcript sample`,
    provenance: `${FIXTURE_PROVENANCE} Botpress import lineage sample.`,
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
    source: "adversarial_catch",
    label: "Adversarial catches",
    count: 5,
    evidence:
      "Synthetic cancellation paraphrases seeded from production traces",
    provenance: `Synthetic fixture provenance: ${FIXTURE_TRACE_ID} + refund_policy_2026.pdf`,
    actionLabel: "Review generated cases",
    confidence: "low",
  },
  {
    id: "src_incident_cluster",
    source: "incident_cluster",
    label: "Incident clusters",
    count: 3,
    evidence: "Latency and routing incident cluster inc_refund_route_042",
    provenance: `${FIXTURE_PROVENANCE} Incident cluster inc_refund_route_042 links affected traces and containment notes.`,
    actionLabel: "Seed incident evals",
    confidence: "high",
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

const PROVENANCE_CASES: EvalProvenanceCase[] = [
  {
    id: "case_prod_refund_window",
    agentId: FIXTURE_AGENT_ID,
    suiteId: "evs_support_smoke",
    sourceType: "production_conversation",
    sourceRef: FIXTURE_TRACE_ID,
    input: "I need to cancel my annual renewal. What happens now?",
    expectedBehavior:
      "Look up the order, cite the May policy, and explain the refund window before final answer.",
    channelType: "web",
    riskTags: ["refund-window", "policy-grounding", "billing"],
    status: "active",
    changePackageRef: "change-package/cp_refund_may_042",
    evidence: `${FIXTURE_TRACE_ID}; refund_policy_2026.pdf#p4`,
  },
  {
    id: "case_comment_exception_cap",
    agentId: FIXTURE_AGENT_ID,
    suiteId: "evs_support_smoke",
    sourceType: "reviewer_comment",
    sourceRef: "comment/th_refund_exception_review#r3",
    input: "Customer requests two partial refunds below the per-call cap.",
    expectedBehavior:
      "Apply the cumulative refund cap across the conversation before approving any refund.",
    channelType: "slack",
    riskTags: ["money-movement", "reviewer-comment", "cap"],
    status: "candidate",
    changePackageRef: "change-package/cp_refund_may_042",
    evidence: "Reviewer resolved comment with expected behavior text.",
  },
  {
    id: "case_handoff_legal_threat",
    agentId: FIXTURE_AGENT_ID,
    suiteId: "evs_routing_regression",
    sourceType: "human_handoff",
    sourceRef: FIXTURE_INBOX_TRACE_ID,
    input: "This is a legal threat if you renew me again.",
    expectedBehavior:
      "Stop automation, preserve context, and route to the retention owner with legal-threat tag.",
    channelType: "voice",
    riskTags: ["legal-threat", "handoff", "voice"],
    status: "active",
    changePackageRef: "change-package/cp_routing_017",
    evidence: "Operator resolution summary and trace handoff span.",
  },
  {
    id: "case_migration_unmapped_condition",
    agentId: FIXTURE_AGENT_ID,
    suiteId: "evs_routing_regression",
    sourceType: "migration_parity_gap",
    sourceRef: `${FIXTURE_MIGRATION_ID}/gap/unmapped-appeal-condition`,
    input: "I want to appeal the cancellation fee.",
    expectedBehavior:
      "Map the imported Botpress appeal branch into an eval-backed policy before cutover.",
    channelType: "whatsapp",
    riskTags: ["botpress-parity", "appeal", "migration"],
    status: "candidate",
    changePackageRef: null,
    evidence: "Parity review found an unmapped condition in the imported flow.",
  },
  {
    id: "case_incident_route_drift",
    agentId: FIXTURE_AGENT_ID,
    suiteId: "evs_routing_regression",
    sourceType: "incident_cluster",
    sourceRef: "incident/inc_refund_route_042",
    input: "Cancel me now. I already talked to support twice.",
    expectedBehavior:
      "Detect repeat-contact frustration, avoid duplicate lookup loops, and escalate with prior context.",
    channelType: "teams",
    riskTags: ["incident", "repeat-contact", "routing"],
    status: "active",
    changePackageRef: "change-package/cp_routing_017",
    evidence: "Incident cluster linked three affected production traces.",
  },
];

const CHANGE_PACKAGE_LINKS: EvalChangePackageLink[] = [
  {
    id: "eval-link-refund-may",
    changePackageRef: "change-package/cp_refund_may_042",
    evalResultsRef: "eval/run/evr_evs_support_smoke_002",
    suiteId: "evs_support_smoke",
    gate: "Required for production canary",
    status: "blocked",
    evidence:
      "One production-derived Spanish refund case still regresses against the draft.",
  },
  {
    id: "eval-link-routing",
    changePackageRef: "change-package/cp_routing_017",
    evalResultsRef: "eval/run/evr_evs_routing_regression_002",
    suiteId: "evs_routing_regression",
    gate: "Required for staging handoff release",
    status: "stale",
    evidence:
      "Incident cluster generated new handoff cases after the package was submitted.",
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
    fixtures: [FIXTURE_TRACE_ID, FIXTURE_SCENE_ID, "refund_policy_2026.pdf#p4"],
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
    fixtures: [FIXTURE_INBOX_TRACE_ID, FIXTURE_SCENE_ID],
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
      source: "production_conversation",
      sourceRef: FIXTURE_TRACE_ID,
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
      evidence: `${FIXTURE_TRACE_ID}, refund_policy_2026.pdf#p4, eval_refunds`,
    },
    {
      caseId: "c3",
      name: "declines unsafe request",
      status: "pass",
      source: "adversarial_catch",
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
): Promise<EvalSuiteListResponse> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture) {
      return { items: FIXTURE_SUITES, evidence_mode: "fixture" };
    }
    return {
      items: [],
      degraded_reason: EVAL_SUITES_CP_API_REQUIRED,
      evidence_mode: "degraded",
    };
  }
  if (!opts.workspaceId?.trim()) {
    return {
      items: [],
      degraded_reason:
        "Workspace context is required before loading eval suites.",
      evidence_mode: "degraded",
    };
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(
    `${base}/workspaces/${encodeURIComponent(opts.workspaceId)}/eval-suites`,
    {
      method: "GET",
      headers: authHeaders(opts),
    },
  );
  if (!res.ok) throw new Error(`listEvalSuites failed: ${res.status}`);
  const body = (await res.json()) as {
    items?: CpEvalSuite[];
    degraded_reason?: string;
    evidence_mode?: EvalSuiteListResponse["evidence_mode"];
  };
  return {
    items: (body.items ?? []).map(mapEvalSuite),
    ...(body.degraded_reason ? { degraded_reason: body.degraded_reason } : {}),
    evidence_mode: body.evidence_mode ?? "live",
  };
}

export async function getEvalSuite(
  suiteId: string,
  opts: EvalsHelperOptions = {},
): Promise<EvalSuiteDetail | null> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture) return fixtureSuiteDetail(suiteId);
    throw new Error(EVAL_SUITE_DETAIL_CP_API_REQUIRED);
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/eval-suites/${suiteId}`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (res.status === 404) {
    throw new Error(
      "cp-api eval suite detail route returned 404. Studio will not turn missing control-plane evidence into a false not-found state.",
    );
  }
  if (!res.ok) throw new Error(`getEvalSuite failed: ${res.status}`);
  const body = (await res.json()) as CpEvalSuite;
  return {
    ...mapEvalSuite(body),
    runs: (body.runs ?? []).map((run) => mapEvalRun(run, body.id ?? "")),
  };
}

export async function getEvalRun(
  runId: string,
  opts: EvalsHelperOptions = {},
): Promise<EvalRunDetail | null> {
  const base = resolveBase(opts);
  if (!base) {
    if (opts.allowFixture) return fixtureRunDetail(runId);
    throw new Error(EVAL_RUN_DETAIL_CP_API_REQUIRED);
  }
  const fetcher = opts.fetcher ?? fetch;
  const res = await fetcher(`${base}/eval-runs/${runId}`, {
    method: "GET",
    headers: authHeaders(opts),
  });
  if (res.status === 404) {
    throw new Error(
      "cp-api eval run detail route returned 404. Studio will not turn missing control-plane evidence into a false not-found state.",
    );
  }
  if (!res.ok) throw new Error(`getEvalRun failed: ${res.status}`);
  const body = (await res.json()) as CpEvalRun;
  return {
    ...mapEvalRun(body),
    cases: (body.cases ?? []).map(mapEvalCaseResult),
  };
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
  options: EvalFoundryModelOptions = {},
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
  const hasFixtureSuite = suites.some(
    (suite) => suite.id === "evs_support_smoke",
  );
  const useFixtureEvidence = options.evidenceMode === "fixture";
  const featuredRun =
    useFixtureEvidence && hasFixtureSuite
      ? fixtureRunDetail("evr_evs_support_smoke_002")
      : null;
  const creationSources = suites.flatMap(
    (suite) => suite.creationSources ?? [],
  );
  const provenanceCases = suites.flatMap(
    (suite) => suite.provenanceCases ?? [],
  );
  const changePackageLinks = suites.flatMap(
    (suite) => suite.changePackageLinks ?? [],
  );
  return {
    creationSources:
      creationSources.length > 0
        ? creationSources
        : useFixtureEvidence && suites.length > 0
          ? CREATION_SOURCES
          : [],
    suiteBuilders,
    featuredResult: featuredRun ? resultDiffForRun(featuredRun) : null,
    provenanceCases:
      provenanceCases.length > 0
        ? provenanceCases
        : useFixtureEvidence && suites.length > 0
          ? PROVENANCE_CASES
          : [],
    changePackageLinks:
      changePackageLinks.length > 0
        ? changePackageLinks
        : useFixtureEvidence && suites.length > 0
          ? CHANGE_PACKAGE_LINKS
          : [],
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
 * POST a new eval suite to ``/v1/workspaces/{workspace_id}/eval-suites``. Returns the created
 * suite summary so the page can refresh in place. Throws on non-2xx
 * so the form can surface the cp-side validation message.
 */
export async function createEvalSuite(
  input: CreateEvalSuiteInput,
  opts: EvalsHelperOptions = {},
): Promise<EvalSuite> {
  const base = resolveBase(opts);
  if (!base) {
    if (!opts.allowFixture) {
      throw new Error("LOOP_CP_API_BASE_URL is required to create eval suites");
    }
    return {
      id: `evs_${Math.random().toString(36).slice(2, 10)}`,
      name: input.name,
      agentId: "",
      cases: 0,
      lastRunAt: null,
      passRate: null,
    };
  }
  if (!opts.workspaceId?.trim()) {
    throw new Error(
      "Workspace context is required before creating eval suites.",
    );
  }
  const fetcher = opts.fetcher ?? fetch;
  const headers = {
    ...authHeaders(opts),
    "content-type": "application/json",
  };
  const res = await fetcher(
    `${base}/workspaces/${encodeURIComponent(opts.workspaceId)}/eval-suites`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        name: input.name,
        dataset_ref: input.dataset_ref,
        metrics: input.metrics,
      }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw new Error(`createEvalSuite failed: ${res.status}`);
  }
  const body = (await res.json()) as CpEvalSuite;
  return mapEvalSuite(body);
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
    if (!opts.allowFixture) {
      throw new Error("LOOP_CP_API_BASE_URL is required to trigger eval runs");
    }
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

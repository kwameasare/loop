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
  expected: string;
  actual: string;
  /** ``status`` of the same case in the baseline run, if known. */
  baselineStatus: EvalCaseStatus | null;
  durationMs: number;
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

function resolveBase(opts: EvalsHelperOptions): string | null {
  const raw =
    opts.baseUrl ??
    (typeof process !== "undefined"
      ? process.env.LOOP_CP_API_BASE_URL ??
        process.env.NEXT_PUBLIC_LOOP_API_URL
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
    name: "support smoke",
    agentId: "agt_demo_support",
    cases: 12,
    lastRunAt: "2025-02-20T18:31:02Z",
    passRate: 0.917,
  },
  {
    id: "evs_routing_regression",
    name: "routing regression",
    agentId: "agt_demo_support",
    cases: 24,
    lastRunAt: "2025-02-20T17:04:55Z",
    passRate: 0.875,
  },
];

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
      expected: "Hello! How can I help?",
      actual: "Hello! How can I help?",
      baselineStatus: "pass",
      durationMs: 412,
    },
    {
      caseId: "c2",
      name: "routes refund to billing",
      status: summary.failed > 0 ? "fail" : "pass",
      expected: "transfer to billing",
      actual: summary.failed > 0 ? "answered directly" : "transfer to billing",
      baselineStatus: "pass",
      durationMs: 689,
    },
    {
      caseId: "c3",
      name: "declines unsafe request",
      status: "pass",
      expected: "refusal",
      actual: "refusal",
      baselineStatus: "pass",
      durationMs: 305,
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
      return { caseId: c.caseId, name: c.name, current: c.status, baseline: null, kind: "new" };
    }
    let kind: EvalDiffEntry["kind"] = "stable";
    if (prev.status === "pass" && c.status !== "pass") kind = "regression";
    else if (prev.status !== "pass" && c.status === "pass") kind = "recovered";
    return { caseId: c.caseId, name: c.name, current: c.status, baseline: prev.status, kind };
  });
}

export function formatPassRate(rate: number | null): string {
  if (rate === null) return "—";
  return `${Math.round(rate * 1000) / 10}%`;
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
  const body = (await res.json()) as Partial<EvalSuite> & { id?: string; name?: string };
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

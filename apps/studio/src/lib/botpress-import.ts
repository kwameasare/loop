/**
 * Botpress import fixture (UX302).
 *
 * Provides a realistic lineage + diff + replay set for the parity
 * harness so the migration parity workspace renders end-to-end without
 * a live import. The fixture deliberately includes one blocking
 * structure diff, one cost regression, and one risk advisory so the UI
 * exercises every severity tone.
 */

import type {
  CutoverPlan,
  DiffEntry,
  ImportLineage,
  ParityReadiness,
  ParityReplayCase,
  RepairSuggestion,
  RollbackTrigger,
} from "./migration-parity";

export interface MigrationParityWorkspace {
  lineage: ImportLineage;
  readiness: ParityReadiness;
  diffs: readonly DiffEntry[];
  replay: readonly ParityReplayCase[];
  repairs: readonly RepairSuggestion[];
  cutover: CutoverPlan;
}

export interface MigrationParityClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
  source?: "botpress";
}

function cpApiBaseUrl(override?: string): string {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) {
    throw new Error("LOOP_CP_API_BASE_URL is required for migration parity calls");
  }
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function headers(opts: MigrationParityClientOptions): Record<string, string> {
  const out: Record<string, string> = { accept: "application/json" };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) out.authorization = `Bearer ${token}`;
  return out;
}

export function createFixtureMigrationParityWorkspace(): MigrationParityWorkspace {
  return {
    lineage: FIXTURE_BOTPRESS_LINEAGE,
    readiness: FIXTURE_BOTPRESS_READINESS,
    diffs: FIXTURE_BOTPRESS_DIFFS,
    replay: FIXTURE_BOTPRESS_REPLAY,
    repairs: FIXTURE_BOTPRESS_REPAIRS,
    cutover: FIXTURE_BOTPRESS_CUTOVER,
  };
}

export async function fetchMigrationParityWorkspace(
  workspaceId: string,
  opts: MigrationParityClientOptions = {},
): Promise<MigrationParityWorkspace> {
  let base: string;
  try {
    base = cpApiBaseUrl(opts.baseUrl);
  } catch (err) {
    if (err instanceof Error && /LOOP_CP_API_BASE_URL/.test(err.message)) {
      return createFixtureMigrationParityWorkspace();
    }
    throw err;
  }
  const params = new URLSearchParams({
    source: opts.source ?? "botpress",
  });
  const response = await (opts.fetcher ?? fetch)(
    `${base}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/migration/parity?${params}`,
    {
      method: "GET",
      headers: headers(opts),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(`cp-api GET migration parity -> ${response.status}`);
  }
  return (await response.json()) as MigrationParityWorkspace;
}

export const FIXTURE_BOTPRESS_LINEAGE: ImportLineage = {
  importId: "imp_bp_2025_02_21",
  source: "botpress",
  archive: "acme-refunds.bpz",
  importedAt: "2025-02-21T08:14:00Z",
  archiveSha:
    "sha256:8a2b9c4f1d6e7a3f0b8c5d9e2a1b4c7d0e3f6a9b2c5d8e1f4a7b0c3d6e9f2a5",
  steps: [
    {
      id: "parse",
      label: "Parse archive",
      status: "ok",
      evidenceRef: "audit/import/imp_bp_2025_02_21#parse",
      detail: "12 flows, 4 KBs, 8 actions, 3 integrations recovered.",
    },
    {
      id: "map",
      label: "Map to Loop primitives",
      status: "warn",
      evidenceRef: "audit/import/imp_bp_2025_02_21#map",
      detail:
        "1 unsupported QnA category mapped to KB tag with explicit lineage note.",
    },
    {
      id: "secrets",
      label: "Re-collect secrets",
      status: "warn",
      evidenceRef: "audit/import/imp_bp_2025_02_21#secrets",
      detail: "2 integration secrets pending re-entry by an admin.",
    },
    {
      id: "compile",
      label: "Compile target build",
      status: "ok",
      evidenceRef: "audit/import/imp_bp_2025_02_21#compile",
      detail: "Target build green; ready for parity replay.",
    },
  ],
};

export const FIXTURE_BOTPRESS_READINESS: ParityReadiness = {
  overallScore: 78,
  parityPassing: 47,
  parityTotal: 60,
  blockingCount: 1,
  advisoryCount: 4,
};

export const FIXTURE_BOTPRESS_DIFFS: readonly DiffEntry[] = [
  {
    id: "diff_str_1",
    mode: "structure",
    sourcePath: "flow.refund.askReason",
    targetPath: "flow.refund.askReason",
    severity: "ok",
    summary: "1:1 mapping; same prompt, same transitions.",
    evidenceRef: "audit/diff/diff_str_1",
  },
  {
    id: "diff_str_2",
    mode: "structure",
    sourcePath: "flow.escalate.qna",
    targetPath: "kb.escalation",
    severity: "blocking",
    summary:
      "QnA node mapped to KB chunk; behavior must be re-verified before promotion.",
    evidenceRef: "audit/diff/diff_str_2",
  },
  {
    id: "diff_beh_1",
    mode: "behavior",
    sourcePath: "flow.refund#happy",
    targetPath: "flow.refund#happy",
    severity: "ok",
    summary: "Identical wording on golden transcript.",
    evidenceRef: "audit/diff/diff_beh_1",
  },
  {
    id: "diff_beh_2",
    mode: "behavior",
    sourcePath: "flow.refund#late",
    targetPath: "flow.refund#late",
    severity: "advisory",
    summary: "Apologetic phrasing tightened (-12 chars, same intent).",
    evidenceRef: "audit/diff/diff_beh_2",
  },
  {
    id: "diff_cost_1",
    mode: "cost",
    sourcePath: "agent.refunds-bot",
    targetPath: "agent.refunds-bot",
    severity: "advisory",
    summary: "Average tokens-per-turn unchanged; cost per turn -$0.001.",
    delta: "-$0.001 / turn",
    evidenceRef: "audit/diff/diff_cost_1",
  },
  {
    id: "diff_cost_2",
    mode: "cost",
    sourcePath: "tool.shopify.read",
    targetPath: "tool.shopify.read",
    severity: "blocking",
    summary: "P95 latency +320ms because target retries on 502.",
    delta: "+320ms p95",
    evidenceRef: "audit/diff/diff_cost_2",
  },
  {
    id: "diff_risk_1",
    mode: "risk",
    sourcePath: "policy.refund.ceiling",
    targetPath: "policy.refund.ceiling",
    severity: "advisory",
    summary: "Refund ceiling moved from hard-coded to policy doc.",
    evidenceRef: "audit/diff/diff_risk_1",
  },
];

export const FIXTURE_BOTPRESS_REPLAY: readonly ParityReplayCase[] = [
  {
    id: "rp_001",
    transcript: "Refund of $48 within 30 days — happy path.",
    status: "pass",
    expectedTarget: "flow.refund.completed",
    observedTarget: "flow.refund.completed",
    evidenceRef: "audit/replay/rp_001",
  },
  {
    id: "rp_002",
    transcript: "Refund of $250 — over policy ceiling.",
    status: "pass",
    expectedTarget: "flow.refund.escalate",
    observedTarget: "flow.refund.escalate",
    evidenceRef: "audit/replay/rp_002",
  },
  {
    id: "rp_003",
    transcript: "Refund request for non-existent order id.",
    status: "regress",
    expectedTarget: "flow.refund.notFound",
    observedTarget: "flow.refund.escalate",
    evidenceRef: "audit/replay/rp_003",
  },
  {
    id: "rp_004",
    transcript: "Customer asks about return shipping label.",
    status: "improve",
    expectedTarget: "flow.escalate.qna",
    observedTarget: "kb.escalation",
    evidenceRef: "audit/replay/rp_004",
  },
];

export const FIXTURE_BOTPRESS_REPAIRS: readonly RepairSuggestion[] = [
  {
    id: "rep_1",
    diffId: "diff_str_2",
    rationale:
      "Promote KB lookup to a tool call so escalation logic stays explicit and auditable.",
    groundingRef: "audit/diff/diff_str_2",
    confidence: "medium",
    patchSummary:
      "Wrap KB lookup in tool `escalation_lookup`; reroute flow.escalate to call it before final reply.",
  },
  {
    id: "rep_2",
    diffId: "diff_cost_2",
    rationale:
      "Add a 1-attempt cap on Shopify 502 retries; current 2-retry policy explains the +320ms p95.",
    groundingRef: "audit/diff/diff_cost_2",
    confidence: "high",
    patchSummary: "Set tool.shopify.read.retries.max from 2 → 1.",
  },
];

export const FIXTURE_BOTPRESS_ROLLBACK: readonly RollbackTrigger[] = [
  {
    id: "rb_regress",
    metric: "regression",
    threshold: ">2 parity regressions in 1h",
    action: "Halt canary; revert traffic to source.",
    evidenceRef: "audit/rollback/rb_regress",
  },
  {
    id: "rb_error",
    metric: "error_rate",
    threshold: "5xx rate >2% over 5m",
    action: "Halt canary; page on-call.",
    evidenceRef: "audit/rollback/rb_error",
  },
  {
    id: "rb_cost",
    metric: "cost_spike",
    threshold: "Cost-per-turn >150% baseline",
    action: "Throttle canary; alert finance + builder.",
    evidenceRef: "audit/rollback/rb_cost",
  },
];

export const FIXTURE_BOTPRESS_CUTOVER: CutoverPlan = {
  id: "cut_bp_1",
  shadow: {
    durationMinutes: 60,
    turns: 1240,
    agreement: 96,
    divergences: 49,
    costPerTurnDelta: "-$0.001",
    evidenceRef: "audit/shadow/cut_bp_1",
  },
  stages: [
    {
      id: "canary_1pct",
      percent: 1,
      durationMinutes: 30,
      status: "passed",
      guardrails: ["error_rate<0.5%", "regression=0"],
    },
    {
      id: "canary_10pct",
      percent: 10,
      durationMinutes: 60,
      status: "in_progress",
      guardrails: ["error_rate<1%", "regression<2", "cost_per_turn<150%"],
    },
    {
      id: "canary_50pct",
      percent: 50,
      durationMinutes: 120,
      status: "pending",
      guardrails: ["error_rate<1%", "regression<2"],
    },
    {
      id: "canary_100pct",
      percent: 100,
      durationMinutes: 0,
      status: "pending",
      guardrails: ["all-stages-passed"],
    },
  ],
  rollbackTriggers: FIXTURE_BOTPRESS_ROLLBACK,
};

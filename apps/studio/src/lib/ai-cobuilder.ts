/**
 * AI Co-Builder model (UX308).
 *
 * Surfaces the contract every AI-assisted edit must satisfy in studio:
 *
 * - **Consent grammar** — every action runs in one of three modes
 *   (Suggest / Edit / Drive), with monotonically increasing autonomy.
 * - **Provenance** — every suggested edit lists the grounding sources
 *   it relied on with their evidence refs.
 * - **Budget / permission** — every action declares the budget cost
 *   and the permission scopes it touches; running an action checks
 *   both against the supplied operator context before mutating.
 * - **Diff** — every edit ships with an exact unified-diff hunk so
 *   the operator sees what will actually change.
 * - **Rubber Duck** — diagnostic fixer that walks the failing trace
 *   and proposes a minimal repair.
 * - **Second Pair of Eyes** — adversarial five-bullet review where
 *   each bullet must include an evidenceRef.
 */

// ---------------------------------------------------------------------------
// Consent grammar
// ---------------------------------------------------------------------------

export type CoBuilderMode = "suggest" | "edit" | "drive";

const MODE_RANK: Record<CoBuilderMode, number> = {
  suggest: 1,
  edit: 2,
  drive: 3,
};

export interface OperatorContext {
  /** Maximum mode the operator has consented to for this surface. */
  maxMode: CoBuilderMode;
  /** Permission scopes the operator currently holds. */
  scopes: readonly string[];
  /** Remaining budget in USD for the surface. */
  budgetRemainingUsd: number;
}

// ---------------------------------------------------------------------------
// Provenance + budget + diff
// ---------------------------------------------------------------------------

export interface Provenance {
  source: string;
  excerpt: string;
  evidenceRef: string;
}

export interface BudgetCost {
  /** Estimated cost in USD. */
  usd: number;
  /** Estimated added latency in milliseconds. */
  latencyMs: number;
}

export interface DiffHunk {
  /** Workspace-relative path. */
  path: string;
  /** Unified-diff body (without header). */
  body: string;
}

// ---------------------------------------------------------------------------
// CoBuilder action
// ---------------------------------------------------------------------------

export interface CoBuilderAction {
  id: string;
  mode: CoBuilderMode;
  title: string;
  rationale: string;
  diff: DiffHunk;
  provenance: readonly Provenance[];
  cost: BudgetCost;
  /** Permission scopes required to apply this action. */
  requiredScopes: readonly string[];
  evidenceRef: string;
}

export class CoBuilderConsentError extends Error {
  readonly code: "mode" | "scope" | "budget";
  constructor(code: "mode" | "scope" | "budget", message: string) {
    super(message);
    this.name = "CoBuilderConsentError";
    this.code = code;
  }
}

export interface ConsentEvaluation {
  ok: boolean;
  reasons: readonly { code: "mode" | "scope" | "budget"; message: string }[];
}

export function evaluateConsent(
  action: CoBuilderAction,
  ctx: OperatorContext,
): ConsentEvaluation {
  const reasons: { code: "mode" | "scope" | "budget"; message: string }[] = [];
  if (MODE_RANK[action.mode] > MODE_RANK[ctx.maxMode]) {
    reasons.push({
      code: "mode",
      message: `Action requires ${action.mode}, operator only consented to ${ctx.maxMode}.`,
    });
  }
  const missingScopes = action.requiredScopes.filter(
    (s) => !ctx.scopes.includes(s),
  );
  if (missingScopes.length > 0) {
    reasons.push({
      code: "scope",
      message: `Missing scopes: ${missingScopes.join(", ")}`,
    });
  }
  if (action.cost.usd > ctx.budgetRemainingUsd) {
    reasons.push({
      code: "budget",
      message: `Cost $${action.cost.usd.toFixed(
        2,
      )} exceeds remaining budget $${ctx.budgetRemainingUsd.toFixed(2)}.`,
    });
  }
  return { ok: reasons.length === 0, reasons };
}

export interface ApplyResult {
  appliedAt: string;
  evidenceRef: string;
}

export function applyAction(
  action: CoBuilderAction,
  ctx: OperatorContext,
  now: () => string = () => new Date().toISOString(),
): ApplyResult {
  const evaluation = evaluateConsent(action, ctx);
  if (!evaluation.ok) {
    const first = evaluation.reasons[0];
    throw new CoBuilderConsentError(first.code, first.message);
  }
  return {
    appliedAt: now(),
    evidenceRef: `${action.evidenceRef}/applied`,
  };
}

// ---------------------------------------------------------------------------
// Rubber Duck
// ---------------------------------------------------------------------------

export interface RubberDuckFinding {
  step: string;
  observation: string;
  evidenceRef: string;
}

export interface RubberDuckDiagnosis {
  caseId: string;
  failureSummary: string;
  findings: readonly RubberDuckFinding[];
  proposedFix: CoBuilderAction;
}

// ---------------------------------------------------------------------------
// Second Pair of Eyes — adversarial five-bullet review
// ---------------------------------------------------------------------------

export type ReviewSeverity = "info" | "warn" | "block";

export interface ReviewBullet {
  id: string;
  severity: ReviewSeverity;
  body: string;
  evidenceRef: string;
}

export interface AdversarialReview {
  actionId: string;
  bullets: readonly ReviewBullet[];
}

export class ReviewShapeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ReviewShapeError";
  }
}

export function validateAdversarialReview(review: AdversarialReview): void {
  if (review.bullets.length !== 5) {
    throw new ReviewShapeError(
      `Adversarial review must have exactly 5 bullets, got ${review.bullets.length}.`,
    );
  }
  for (const b of review.bullets) {
    if (!b.evidenceRef.trim()) {
      throw new ReviewShapeError(
        `Bullet ${b.id} is missing evidenceRef.`,
      );
    }
  }
}

export function blockingBullets(
  review: AdversarialReview,
): readonly ReviewBullet[] {
  return review.bullets.filter((b) => b.severity === "block");
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const FIXTURE_ACTION_SUGGEST: CoBuilderAction = {
  id: "act_offer_callback",
  mode: "suggest",
  title: "Offer callback before transfer for refunds > $200",
  rationale:
    "Comment thread th_refund_escalate concluded callback should precede transfer.",
  diff: {
    path: "agents/refunds-bot/flow/escalate.ts",
    body:
      "@@ -12,6 +12,11 @@\n   if (amount > CEILING) {\n+    if (await offerCallback(user)) {\n+      return { kind: 'callback_scheduled' };\n+    }\n     return { kind: 'transfer' };\n   }",
  },
  provenance: [
    {
      source: "comment thread th_refund_escalate",
      excerpt: "We should offer callback before transfer for amounts over $200.",
      evidenceRef: "audit/comments/cm_1",
    },
    {
      source: "policy doc refund-policy@v3",
      excerpt: "High-value refunds require human review or callback.",
      evidenceRef: "audit/kb/refund-policy-v3",
    },
  ],
  cost: { usd: 0.04, latencyMs: 320 },
  requiredScopes: ["agent:edit", "flow:write"],
  evidenceRef: "audit/cobuilder/act_offer_callback",
};

export const FIXTURE_ACTION_DRIVE: CoBuilderAction = {
  id: "act_drive_kb_rebuild",
  mode: "drive",
  title: "Rebuild KB index after policy update",
  rationale: "KB chunks reference outdated return-window; rebuild required.",
  diff: {
    path: "agents/refunds-bot/kb/index.json",
    body: "@@ -1,3 +1,3 @@\n-{ \"version\": 9 }\n+{ \"version\": 10 }",
  },
  provenance: [
    {
      source: "policy doc refund-policy@v4",
      excerpt: "Return window updated from 30 to 14 days.",
      evidenceRef: "audit/kb/refund-policy-v4",
    },
  ],
  cost: { usd: 1.2, latencyMs: 60_000 },
  requiredScopes: ["kb:rebuild"],
  evidenceRef: "audit/cobuilder/act_drive_kb_rebuild",
};

export const FIXTURE_RUBBER_DUCK: RubberDuckDiagnosis = {
  caseId: "rd_001",
  failureSummary:
    "Eval refund_over_ceiling expected escalate; got auto-approve.",
  findings: [
    {
      step: "guardrail.refund_ceiling",
      observation: "Guardrail short-circuited before policy check.",
      evidenceRef: "audit/rubberduck/rd_001/step_1",
    },
    {
      step: "tool.shopify.read",
      observation: "Tool read order; ceiling not consulted.",
      evidenceRef: "audit/rubberduck/rd_001/step_2",
    },
    {
      step: "model.policy_reasoner",
      observation: "Reasoner output 'auto_approve' due to missing ceiling input.",
      evidenceRef: "audit/rubberduck/rd_001/step_3",
    },
  ],
  proposedFix: {
    id: "act_pass_ceiling_to_reasoner",
    mode: "edit",
    title: "Pass refund-ceiling into policy reasoner",
    rationale:
      "Reasoner cannot enforce ceiling without it being passed through context.",
    diff: {
      path: "agents/refunds-bot/flow/policy-reasoner.ts",
      body:
        "@@ -8,6 +8,7 @@\n const ctx = {\n   amount: order.amount,\n+  refundCeiling: POLICY.refundCeiling,\n   user,\n };",
    },
    provenance: [
      {
        source: "trace pd_001 ev_2",
        excerpt: "Reasoner had no refundCeiling field in its context.",
        evidenceRef: "audit/trace/pd_001/ev_2",
      },
    ],
    cost: { usd: 0.02, latencyMs: 80 },
    requiredScopes: ["agent:edit"],
    evidenceRef: "audit/cobuilder/act_pass_ceiling_to_reasoner",
  },
};

export const FIXTURE_REVIEW: AdversarialReview = {
  actionId: "act_offer_callback",
  bullets: [
    {
      id: "rb_1",
      severity: "warn",
      body: "Callback adds latency; verify p95 stays under SLO.",
      evidenceRef: "audit/review/rb_1",
    },
    {
      id: "rb_2",
      severity: "info",
      body: "EU SMS callback path is untested.",
      evidenceRef: "audit/review/rb_2",
    },
    {
      id: "rb_3",
      severity: "block",
      body: "Callback consent string missing from disclosures.json.",
      evidenceRef: "audit/review/rb_3",
    },
    {
      id: "rb_4",
      severity: "warn",
      body: "Eval coverage for callback decline path is thin.",
      evidenceRef: "audit/review/rb_4",
    },
    {
      id: "rb_5",
      severity: "info",
      body: "Operator tone guide should be updated to reference callback.",
      evidenceRef: "audit/review/rb_5",
    },
  ],
};

export const FIXTURE_OPERATOR: OperatorContext = {
  maxMode: "edit",
  scopes: ["agent:edit", "flow:write"],
  budgetRemainingUsd: 5,
};

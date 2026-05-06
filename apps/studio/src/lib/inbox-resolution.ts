/**
 * Operator resolution → eval case.
 *
 * Canonical target §21.3: "At resolution: save as eval case, expected
 * outcome from operator resolution, linked trace, linked failure
 * reason, attached tool/retrieval evidence."
 *
 * §15.1 lists "operator resolutions" as a primary eval-case source.
 *
 * This module is the pure model that backs the
 * `ResolutionToEval` and `ConversationEvidence` components. It is
 * intentionally side-effect-free so it can be unit-tested without a
 * server.
 */

export type EvidenceTrace = {
  id: string;
  step: string;
  detail: string;
  status: "ok" | "warn" | "error";
  evidenceRef: string;
};

export type EvidenceMemory = {
  id: string;
  scope: "session" | "user" | "org";
  key: string;
  value: string;
  evidenceRef: string;
};

export type EvidenceTool = {
  id: string;
  name: string;
  status: "ok" | "warn" | "error";
  detail: string;
  evidenceRef: string;
};

export type EvidenceRetrieval = {
  id: string;
  source: string;
  score: number;
  excerpt: string;
  evidenceRef: string;
};

export type EvidenceContext = {
  conversation_id: string;
  trace: readonly EvidenceTrace[];
  memory: readonly EvidenceMemory[];
  tools: readonly EvidenceTool[];
  retrieval: readonly EvidenceRetrieval[];
  /** Stable trace id used as the eval's linked trace. */
  resolutionEvidenceRef: string;
};

export type ResolutionOutcome = "resolved" | "handback" | "abandoned";

export type ResolutionDraft = {
  outcome: ResolutionOutcome;
  expectedOutcome: string;
  failureReason: string;
  saveAsEval: boolean;
};

export type EvalCaseFromResolution = {
  id: string;
  title: string;
  expectedOutcome: string;
  failureReason: string;
  linkedTrace: string;
  attachments: readonly string[];
  source: "operator-resolution";
};

export class ResolutionDraftError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResolutionDraftError";
  }
}

/**
 * Build an eval case from an operator's resolution.
 *
 * Throws `ResolutionDraftError` if `saveAsEval` is true but the draft
 * is missing a required field. The pure-function shape lets the UI
 * stay optimistic and the cp-api adapter own the actual POST.
 */
export function buildEvalCaseFromResolution(
  ctx: EvidenceContext,
  draft: ResolutionDraft,
): EvalCaseFromResolution {
  if (!draft.saveAsEval) {
    throw new ResolutionDraftError("saveAsEval must be true to build a case");
  }
  const expected = draft.expectedOutcome.trim();
  if (expected.length === 0) {
    throw new ResolutionDraftError("expectedOutcome is required");
  }
  const failure = draft.failureReason.trim();
  if (failure.length === 0) {
    throw new ResolutionDraftError("failureReason is required");
  }
  return {
    id: `eval_${ctx.conversation_id}`,
    title: `Resolution from ${ctx.conversation_id}`,
    expectedOutcome: expected,
    failureReason: failure,
    linkedTrace: ctx.resolutionEvidenceRef,
    attachments: [
      ...ctx.tools.map((t) => t.evidenceRef),
      ...ctx.retrieval.map((r) => r.evidenceRef),
    ],
    source: "operator-resolution",
  };
}

export const FIXTURE_EVIDENCE_CONTEXT: EvidenceContext = {
  conversation_id: "thr_8823",
  resolutionEvidenceRef: "trace/thr_8823",
  trace: [
    {
      id: "step_1",
      step: "Intent classify",
      detail: "refund_request (0.94)",
      status: "ok",
      evidenceRef: "trace/thr_8823#1",
    },
    {
      id: "step_2",
      step: "Tool call",
      detail: "ShopifyOrders.read order_id=1042 → 502",
      status: "error",
      evidenceRef: "trace/thr_8823#2",
    },
    {
      id: "step_3",
      step: "Retry tool",
      detail: "ShopifyOrders.read order_id=1042 → 502",
      status: "error",
      evidenceRef: "trace/thr_8823#3",
    },
    {
      id: "step_4",
      step: "Pause for human",
      detail: "Tool failure threshold reached.",
      status: "warn",
      evidenceRef: "trace/thr_8823#4",
    },
  ],
  memory: [
    {
      id: "mem_1",
      scope: "user",
      key: "vip_tier",
      value: "gold",
      evidenceRef: "memory/mei.c#vip",
    },
    {
      id: "mem_2",
      scope: "session",
      key: "channel",
      value: "whatsapp",
      evidenceRef: "memory/thr_8823#channel",
    },
  ],
  tools: [
    {
      id: "tool_1",
      name: "ShopifyOrders.read",
      status: "error",
      detail: "Upstream 502, retried with backoff.",
      evidenceRef: "tool/shopify-orders#thr_8823",
    },
    {
      id: "tool_2",
      name: "RefundPolicy.lookup",
      status: "ok",
      detail: "Eligible for one-click refund up to $50.",
      evidenceRef: "tool/refund-policy#thr_8823",
    },
  ],
  retrieval: [
    {
      id: "rtv_1",
      source: "kb/refund-policy.md#section-2",
      score: 0.91,
      excerpt: "Orders under $50 are eligible for one-click refund...",
      evidenceRef: "kb/refund-policy.md#section-2",
    },
    {
      id: "rtv_2",
      source: "kb/escalation.md#tool-failure",
      score: 0.78,
      excerpt: "When upstream tool calls fail twice, escalate to a human...",
      evidenceRef: "kb/escalation.md#tool-failure",
    },
  ],
};

export const FIXTURE_SUGGESTED_DRAFT: string =
  "Hi Mei — I see the order on our side. I've issued a one-click refund and emailed the receipt. You should see it within 3–5 business days.";

export const DEFAULT_RESOLUTION: ResolutionDraft = {
  outcome: "resolved",
  expectedOutcome:
    "Issue refund and confirm the email; ShopifyOrders.read should be retried with circuit breaker.",
  failureReason: "Tool flakiness on ShopifyOrders.read",
  saveAsEval: true,
};

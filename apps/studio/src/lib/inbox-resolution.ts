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

export interface ResolutionEvalClientOptions {
  fetcher?: typeof fetch;
  token?: string;
  baseUrl?: string;
}

function cpApiBaseUrl(override?: string): string | null {
  const raw =
    override ??
    process.env.LOOP_CP_API_BASE_URL ??
    process.env.NEXT_PUBLIC_LOOP_API_URL;
  if (!raw) return null;
  const trimmed = raw.replace(/\/$/, "");
  return trimmed.endsWith("/v1") ? trimmed : `${trimmed}/v1`;
}

function resolutionHeaders(
  opts: ResolutionEvalClientOptions,
): Record<string, string> {
  const headers: Record<string, string> = {
    accept: "application/json",
    "content-type": "application/json",
  };
  const token = opts.token ?? process.env.LOOP_TOKEN;
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

export class ResolutionDraftError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ResolutionDraftError";
  }
}

export function createEvidenceContextFromConversation(args: {
  conversation_id: string;
  messages: readonly {
    id: string;
    role: "user" | "assistant" | "operator" | "system";
    body: string;
    created_at_ms: number;
  }[];
}): EvidenceContext {
  const ordered = [...args.messages].sort(
    (a, b) => a.created_at_ms - b.created_at_ms,
  );
  const trace: EvidenceTrace[] = ordered.slice(-6).map((message, index) => {
    const lower = message.body.toLowerCase();
    const status =
      /error|failed|502|timeout|cannot|unable/.test(lower)
        ? "error"
        : /legal|escalat|human|operator|review/.test(lower)
          ? "warn"
          : "ok";
    return {
      id: `step_${index + 1}`,
      step: `${message.role} turn`,
      detail:
        message.body.length > 140
          ? `${message.body.slice(0, 137)}...`
          : message.body,
      status,
      evidenceRef: `conversation/${args.conversation_id}#${message.id}`,
    };
  });
  const joined = ordered.map((message) => message.body).join("\n").toLowerCase();
  const memory: EvidenceMemory[] = [];
  if (/vip|premium|gold/.test(joined)) {
    memory.push({
      id: "mem_customer_tier",
      scope: "session",
      key: "customer_tier_hint",
      value: "premium-or-vip mentioned in conversation",
      evidenceRef: `memory/${args.conversation_id}#customer_tier_hint`,
    });
  }
  if (/spanish|español|english|français|french|german|deutsch/.test(joined)) {
    memory.push({
      id: "mem_language",
      scope: "session",
      key: "language_hint",
      value: "language preference mentioned in conversation",
      evidenceRef: `memory/${args.conversation_id}#language_hint`,
    });
  }
  const tools: EvidenceTool[] = [];
  if (/order|refund|charge|payment|renewal|subscription/.test(joined)) {
    tools.push({
      id: "tool_order_lookup",
      name: "OrderLookup.read",
      status: /502|timeout|failed|error/.test(joined) ? "error" : "ok",
      detail: /502|timeout|failed|error/.test(joined)
        ? "Conversation indicates the order or payment lookup path failed."
        : "Conversation contains order/payment context that should be checked before resolution.",
      evidenceRef: `tool/order-lookup#${args.conversation_id}`,
    });
  }
  if (/legal|lawyer|attorney|human|operator|escalat|manager/.test(joined)) {
    tools.push({
      id: "tool_handoff_policy",
      name: "HandoffPolicy.evaluate",
      status: "warn",
      detail: "Conversation mentions escalation or human handoff conditions.",
      evidenceRef: `tool/handoff-policy#${args.conversation_id}`,
    });
  }
  const retrieval: EvidenceRetrieval[] = [];
  if (/refund|return|cancel|renewal|subscription/.test(joined)) {
    retrieval.push({
      id: "rtv_refund_policy",
      source: "kb/refund-and-cancellation-policy",
      score: 0.84,
      excerpt:
        "Use the current refund and cancellation policy before promising outcomes.",
      evidenceRef: `kb/refund-and-cancellation-policy#${args.conversation_id}`,
    });
  }
  if (/legal|lawyer|attorney|human|operator|escalat/.test(joined)) {
    retrieval.push({
      id: "rtv_escalation_policy",
      source: "kb/escalation-policy",
      score: 0.8,
      excerpt:
        "Escalate legal threats, explicit human requests, and high-risk payment disputes.",
      evidenceRef: `kb/escalation-policy#${args.conversation_id}`,
    });
  }
  return {
    conversation_id: args.conversation_id,
    trace:
      trace.length > 0
        ? trace
        : [
            {
              id: "step_empty",
              step: "Conversation load",
              detail: "No transcript messages are available yet.",
              status: "warn",
              evidenceRef: `conversation/${args.conversation_id}#empty`,
            },
          ],
    memory,
    tools,
    retrieval,
    resolutionEvidenceRef: `trace/${args.conversation_id}`,
  };
}

export function suggestOperatorDraftFromConversation(
  messages: readonly { role: string; body: string; created_at_ms: number }[],
): string {
  const latestUser = [...messages]
    .sort((a, b) => b.created_at_ms - a.created_at_ms)
    .find((message) => message.role === "user");
  const body = latestUser?.body.toLowerCase() ?? "";
  if (/legal|lawyer|attorney/.test(body)) {
    return "I understand this is sensitive. I’m escalating this to the right human specialist and attaching the conversation trace so they can review the exact policy and account context before responding.";
  }
  if (/refund|charge|payment|renewal|cancel/.test(body)) {
    return "Thanks for the details. I’m checking the current order and refund policy evidence now, then I’ll confirm the safest next step with a traceable explanation.";
  }
  if (/human|person|operator|agent/.test(body)) {
    return "I’m here with you now. I’ve paused the agent and I’m reviewing the conversation evidence before replying.";
  }
  return "I’m reviewing the conversation context and will respond with the exact next step in a moment.";
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

export async function saveResolutionEvalCase(
  workspaceId: string,
  draft: EvalCaseFromResolution,
  opts: ResolutionEvalClientOptions = {},
): Promise<{ ok: boolean; error?: string; suite_id?: string; case_id?: string }> {
  const base = cpApiBaseUrl(opts.baseUrl);
  if (!base) {
    return { ok: true, suite_id: "operator-resolutions", case_id: draft.id };
  }
  const fetcher = opts.fetcher ?? fetch;
  const response = await fetcher(
    `${base}/workspaces/${encodeURIComponent(
      workspaceId,
    )}/eval-cases/from-resolution`,
    {
      method: "POST",
      headers: resolutionHeaders(opts),
      body: JSON.stringify(draft),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    return {
      ok: false,
      error: `cp-api save resolution eval -> ${response.status}`,
    };
  }
  const body = (await response.json()) as {
    ok?: boolean;
    suite_id?: string;
    case_id?: string;
  };
  const result: {
    ok: boolean;
    error?: string;
    suite_id?: string;
    case_id?: string;
  } = { ok: body.ok ?? true };
  if (body.suite_id) result.suite_id = body.suite_id;
  if (body.case_id) result.case_id = body.case_id;
  return result;
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

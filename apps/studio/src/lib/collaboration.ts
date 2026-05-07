/**
 * Collaboration model (UX307).
 *
 * Covers presence, changesets with multi-axis approvals
 * (behavior / eval / cost / latency), and pair-debugging with a
 * shared trace playhead.
 */

import { TRACE_CLIENT, TRACE_PRODUCER, TRACE_SERVER } from "@/lib/design-tokens";
import { listAuditEvents, type ListAuditEventsOptions } from "@/lib/audit-events";
import {
  fetchTraceByTurnId,
  searchTraces,
  type Trace,
  type TracesClientOptions,
} from "@/lib/traces";
import {
  cpJson,
  cpWebSocketUrl,
  type UxWireupClientOptions,
} from "@/lib/ux-wireup";

// ---------------------------------------------------------------------------
// Presence
// ---------------------------------------------------------------------------

export type PresenceStatus = "active" | "idle" | "viewing";

export interface PresenceUser {
  id: string;
  display: string;
  color: string;
  status: PresenceStatus;
  /** Object id the user is currently looking at, if any. */
  focus?: string;
}

// ---------------------------------------------------------------------------
// Changeset approvals
// ---------------------------------------------------------------------------

export type ApprovalAxis = "behavior" | "eval" | "cost" | "latency";

export type ApprovalState = "pending" | "approved" | "rejected" | "changes_requested";

export interface AxisApproval {
  axis: ApprovalAxis;
  state: ApprovalState;
  reviewer?: string;
  decidedAt?: string;
  invalidatedAt?: string;
  /** Free-text rationale; required for rejected / changes_requested. */
  rationale?: string;
  evidenceRef: string;
}

export interface Changeset {
  id: string;
  title: string;
  authorDisplay: string;
  createdAt: string;
  approvals: readonly AxisApproval[];
  evidenceRef: string;
}

const REQUIRED_AXES: readonly ApprovalAxis[] = [
  "behavior",
  "eval",
  "cost",
  "latency",
];

export class ApprovalValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApprovalValidationError";
  }
}

export function validateChangesetApprovals(cs: Changeset): void {
  const seen = new Set<ApprovalAxis>();
  for (const a of cs.approvals) {
    if (seen.has(a.axis)) {
      throw new ApprovalValidationError(`duplicate approval axis: ${a.axis}`);
    }
    seen.add(a.axis);
    if (
      (a.state === "rejected" || a.state === "changes_requested") &&
      !(a.rationale && a.rationale.trim())
    ) {
      throw new ApprovalValidationError(
        `${a.axis} requires rationale when ${a.state}`,
      );
    }
  }
  for (const axis of REQUIRED_AXES) {
    if (!seen.has(axis)) {
      throw new ApprovalValidationError(`missing required axis: ${axis}`);
    }
  }
}

export function isChangesetReadyToMerge(cs: Changeset): boolean {
  try {
    validateChangesetApprovals(cs);
  } catch {
    return false;
  }
  return cs.approvals.every((a) => a.state === "approved");
}

export function pendingAxes(cs: Changeset): readonly ApprovalAxis[] {
  return cs.approvals
    .filter((a) => a.state !== "approved")
    .map((a) => a.axis);
}

// ---------------------------------------------------------------------------
// Pair debugging — shared trace playhead
// ---------------------------------------------------------------------------

export interface TraceEvent {
  id: string;
  ts: string;
  /** Monotonic offset in milliseconds from trace start. */
  offsetMs: number;
  kind: "tool_call" | "model_call" | "guardrail" | "user_turn" | "agent_turn";
  summary: string;
  evidenceRef: string;
}

export interface PairDebugSession {
  id: string;
  trace: readonly TraceEvent[];
  participants: readonly PresenceUser[];
  /** Current playhead offset in ms; clamped within trace range. */
  playheadMs: number;
}

export interface CollaborationWorkspace {
  presence: readonly PresenceUser[];
  changeset: Changeset;
  pairDebug: PairDebugSession;
}

export interface CommentResolutionPayload {
  expected_behavior: string;
  failure_reason: string;
  also_create_eval_case?: boolean;
  source_trace?: string;
}

export interface CommentResolutionResult {
  comment_id: string;
  resolved_by: string;
  eval_case_created: boolean;
  case_id: string | null;
  expected_behavior: string;
  failure_reason: string;
  source_trace?: string | null;
}

export class PlayheadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "PlayheadError";
  }
}

export function clampPlayhead(
  session: PairDebugSession,
  offsetMs: number,
): number {
  if (session.trace.length === 0) {
    throw new PlayheadError("trace is empty");
  }
  const first = session.trace[0]!;
  const last = session.trace[session.trace.length - 1]!;
  const min = first.offsetMs;
  const max = last.offsetMs;
  if (Number.isNaN(offsetMs)) {
    throw new PlayheadError("offsetMs must be a number");
  }
  if (offsetMs < min) return min;
  if (offsetMs > max) return max;
  return offsetMs;
}

export function eventAtPlayhead(
  session: PairDebugSession,
): TraceEvent | undefined {
  if (session.trace.length === 0) return undefined;
  // pick latest event whose offset <= playhead.
  let candidate: TraceEvent | undefined;
  for (const ev of session.trace) {
    if (ev.offsetMs <= session.playheadMs) candidate = ev;
    else break;
  }
  return candidate ?? session.trace[0];
}

export function setPlayhead(
  session: PairDebugSession,
  offsetMs: number,
): PairDebugSession {
  return {
    ...session,
    playheadMs: clampPlayhead(session, offsetMs),
  };
}

export function presenceSocketUrl(
  workspaceId: string,
  opts: { baseUrl?: string; callerSub?: string } = {},
): string | null {
  return cpWebSocketUrl(
    `/workspaces/${encodeURIComponent(workspaceId)}/presence`,
    opts,
  );
}

export async function resolveCommentAsEvalCase(
  agentId: string,
  commentId: string,
  payload: CommentResolutionPayload,
  opts: UxWireupClientOptions = {},
): Promise<CommentResolutionResult> {
  return cpJson<CommentResolutionResult>(
    `/agents/${encodeURIComponent(agentId)}/comments/${encodeURIComponent(
      commentId,
    )}/resolve`,
    {
      ...opts,
      method: "POST",
      body: {
        ...payload,
        also_create_eval_case: payload.also_create_eval_case ?? true,
      },
      fallback: {
        comment_id: commentId,
        resolved_by: "local-builder",
        eval_case_created: payload.also_create_eval_case ?? true,
        case_id: `eval_comment_${commentId}`,
        expected_behavior: payload.expected_behavior,
        failure_reason: payload.failure_reason,
        source_trace: payload.source_trace ?? null,
      },
    },
  );
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const FIXTURE_PRESENCE: readonly PresenceUser[] = [
  {
    id: "u_amaya",
    display: "Amaya O.",
    color: TRACE_SERVER,
    status: "active",
    focus: "node_refund_escalate",
  },
  {
    id: "u_kojo",
    display: "Kojo A.",
    color: TRACE_CLIENT,
    status: "viewing",
    focus: "node_refund_escalate",
  },
  {
    id: "u_zara",
    display: "Zara N.",
    color: TRACE_PRODUCER,
    status: "idle",
  },
];

export const FIXTURE_CHANGESET: Changeset = {
  id: "cs_refund_v35",
  title: "refunds-bot v35 — callback before transfer",
  authorDisplay: "Amaya O.",
  createdAt: "2025-02-21T11:00:00Z",
  evidenceRef: "audit/changeset/cs_refund_v35",
  approvals: [
    {
      axis: "behavior",
      state: "approved",
      reviewer: "Kojo A.",
      decidedAt: "2025-02-21T11:30:00Z",
      evidenceRef: "audit/changeset/cs_refund_v35/behavior",
    },
    {
      axis: "eval",
      state: "approved",
      reviewer: "Eval Bot",
      decidedAt: "2025-02-21T11:31:00Z",
      evidenceRef: "audit/changeset/cs_refund_v35/eval",
    },
    {
      axis: "cost",
      state: "changes_requested",
      reviewer: "FinOps",
      decidedAt: "2025-02-21T11:35:00Z",
      rationale: "p95 cost +18% over budget; reduce model fanout.",
      evidenceRef: "audit/changeset/cs_refund_v35/cost",
    },
    {
      axis: "latency",
      state: "pending",
      evidenceRef: "audit/changeset/cs_refund_v35/latency",
    },
  ],
};

export const FIXTURE_PAIR_DEBUG: PairDebugSession = {
  id: "pd_001",
  participants: FIXTURE_PRESENCE.slice(0, 2),
  playheadMs: 1200,
  trace: [
    {
      id: "ev_1",
      ts: "2025-02-21T11:00:00.000Z",
      offsetMs: 0,
      kind: "user_turn",
      summary: "User asks for refund of $250.",
      evidenceRef: "audit/trace/pd_001/ev_1",
    },
    {
      id: "ev_2",
      ts: "2025-02-21T11:00:00.620Z",
      offsetMs: 620,
      kind: "model_call",
      summary: "Refund-policy reasoner classifies above ceiling.",
      evidenceRef: "audit/trace/pd_001/ev_2",
    },
    {
      id: "ev_3",
      ts: "2025-02-21T11:00:01.180Z",
      offsetMs: 1180,
      kind: "tool_call",
      summary: "Shopify lookup confirms order eligibility.",
      evidenceRef: "audit/trace/pd_001/ev_3",
    },
    {
      id: "ev_4",
      ts: "2025-02-21T11:00:01.900Z",
      offsetMs: 1900,
      kind: "guardrail",
      summary: "Guardrail blocks auto-approve, routes to escalate.",
      evidenceRef: "audit/trace/pd_001/ev_4",
    },
    {
      id: "ev_5",
      ts: "2025-02-21T11:00:02.600Z",
      offsetMs: 2600,
      kind: "agent_turn",
      summary: "Agent offers callback before transfer.",
      evidenceRef: "audit/trace/pd_001/ev_5",
    },
  ],
};

function traceKind(category: Trace["spans"][number]["category"]): TraceEvent["kind"] {
  if (category === "tool" || category === "retrieval") return "tool_call";
  if (category === "llm") return "model_call";
  if (category === "policy" || category === "budget") return "guardrail";
  if (category === "channel") return "user_turn";
  return "agent_turn";
}

function pairDebugFromTrace(trace: Trace): PairDebugSession {
  const spans = [...trace.spans].sort((a, b) => a.start_ns - b.start_ns);
  const traceEvents: TraceEvent[] = spans.map((span) => ({
    id: span.id,
    ts: new Date(Date.UTC(2026, 4, 7) + span.start_ns / 1_000_000).toISOString(),
    offsetMs: Math.round(span.start_ns / 1_000_000),
    kind: traceKind(span.category),
    summary: `${span.name} ${span.status}`,
    evidenceRef: `${trace.id}/${span.id}`,
  }));
  return {
    id: `pd_${trace.id.slice(0, 12)}`,
    participants: FIXTURE_PRESENCE.slice(0, 1),
    playheadMs: traceEvents[0]?.offsetMs ?? 0,
    trace: traceEvents.length > 0 ? traceEvents : FIXTURE_PAIR_DEBUG.trace,
  };
}

function changesetFromAudit(
  workspaceId: string,
  latestAction: string | null,
): Changeset {
  const evidenceRef = latestAction
    ? `audit/${workspaceId}/${latestAction}`
    : `audit/${workspaceId}/no-recent-write`;
  return {
    id: `cs_${workspaceId.slice(0, 8)}`,
    title: latestAction
      ? `Review impact of ${latestAction}`
      : "No pending changeset in the live audit window",
    authorDisplay: latestAction ? "Workspace actor" : "Loop system",
    createdAt: new Date().toISOString(),
    evidenceRef,
    approvals: [
      {
        axis: "behavior",
        state: latestAction ? "pending" : "approved",
        evidenceRef: `${evidenceRef}/behavior`,
      },
      {
        axis: "eval",
        state: latestAction ? "pending" : "approved",
        evidenceRef: `${evidenceRef}/eval`,
      },
      {
        axis: "cost",
        state: "approved",
        reviewer: "Cost guard",
        decidedAt: new Date().toISOString(),
        evidenceRef: `${evidenceRef}/cost`,
      },
      {
        axis: "latency",
        state: "approved",
        reviewer: "Latency guard",
        decidedAt: new Date().toISOString(),
        evidenceRef: `${evidenceRef}/latency`,
      },
    ],
  };
}

export async function fetchCollaborationWorkspace(
  workspaceId: string,
  opts: TracesClientOptions & ListAuditEventsOptions = {},
): Promise<CollaborationWorkspace> {
  try {
    const [traceResult, auditResult] = await Promise.all([
      searchTraces(workspaceId, { page_size: 1 }, opts),
      listAuditEvents(workspaceId, { ...opts, limit: 20 }),
    ]);
    const traceId = traceResult.traces[0]?.id;
    const trace = traceId
      ? await fetchTraceByTurnId(traceId, opts).catch(() => null)
      : null;
    const latestAction = auditResult.events[0]?.action ?? null;
    return {
      presence: [
        {
          id: "current_builder",
          display: "Current builder",
          color: TRACE_SERVER,
          status: "active",
          focus: traceId ? `trace/${traceId.slice(0, 8)}` : "workspace",
        },
      ],
      changeset: changesetFromAudit(workspaceId, latestAction),
      pairDebug: trace ? pairDebugFromTrace(trace) : FIXTURE_PAIR_DEBUG,
    };
  } catch (err) {
    if (
      err instanceof Error &&
      /LOOP_CP_API_BASE_URL is required/.test(err.message)
    ) {
      return {
        presence: FIXTURE_PRESENCE,
        changeset: FIXTURE_CHANGESET,
        pairDebug: FIXTURE_PAIR_DEBUG,
      };
    }
    throw err;
  }
}

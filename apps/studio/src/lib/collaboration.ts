/**
 * Collaboration model (UX307).
 *
 * Covers presence, changesets with multi-axis approvals
 * (behavior / eval / cost / latency), and pair-debugging with a
 * shared trace playhead.
 */

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
  const min = session.trace[0].offsetMs;
  const max = session.trace[session.trace.length - 1].offsetMs;
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

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const FIXTURE_PRESENCE: readonly PresenceUser[] = [
  {
    id: "u_amaya",
    display: "Amaya O.",
    color: "#0ea5e9",
    status: "active",
    focus: "node_refund_escalate",
  },
  {
    id: "u_kojo",
    display: "Kojo A.",
    color: "#a855f7",
    status: "viewing",
    focus: "node_refund_escalate",
  },
  {
    id: "u_zara",
    display: "Zara N.",
    color: "#f97316",
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

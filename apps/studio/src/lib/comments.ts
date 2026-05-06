/**
 * Comments model (UX307).
 *
 * Comments anchor to stable object IDs that persist across versions of
 * the underlying surface (a flow node, a transcript turn, an eval
 * spec). Each comment records the version it was authored against so a
 * "stale" badge can surface in the UI when the underlying object has
 * moved on, without ever orphaning the thread.
 *
 * Resolution is first-class: a comment thread can resolve into an
 * eval spec so the conversation captures a permanent regression test.
 */

export type CommentObjectKind =
  | "flow_node"
  | "transcript_turn"
  | "eval_case"
  | "agent"
  | "kb_chunk";

export interface CommentAnchor {
  /** Stable id assigned at creation; immutable across versions. */
  objectId: string;
  kind: CommentObjectKind;
  /** Version of the object the comment was authored against. */
  authoredAt: string;
}

export interface Comment {
  id: string;
  threadId: string;
  authorId: string;
  authorDisplay: string;
  body: string;
  createdAt: string;
  anchor: CommentAnchor;
  evidenceRef: string;
}

export interface CommentThread {
  id: string;
  anchor: CommentAnchor;
  /** Latest version observed for the anchored object. */
  observedAt: string;
  comments: readonly Comment[];
  resolution?: ThreadResolution;
}

export type ResolutionKind = "eval_spec" | "wontfix" | "duplicate";

export interface ThreadResolution {
  kind: ResolutionKind;
  /** Set when kind === "eval_spec". */
  evalSpecId?: string;
  resolvedBy: string;
  resolvedAt: string;
  evidenceRef: string;
}

export function isThreadStale(thread: CommentThread): boolean {
  return thread.observedAt !== thread.anchor.authoredAt;
}

export class ThreadResolutionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ThreadResolutionError";
  }
}

export interface ResolveAsEvalInput {
  threadId: string;
  evalSpecId: string;
  resolvedBy: string;
  resolvedAt: string;
  evidenceRef: string;
}

export function resolveThreadAsEval(
  thread: CommentThread,
  input: ResolveAsEvalInput,
): CommentThread {
  if (thread.id !== input.threadId) {
    throw new ThreadResolutionError(
      `threadId mismatch: ${thread.id} vs ${input.threadId}`,
    );
  }
  if (thread.resolution) {
    throw new ThreadResolutionError(`thread ${thread.id} is already resolved`);
  }
  if (!input.evalSpecId.trim()) {
    throw new ThreadResolutionError("evalSpecId is required");
  }
  return {
    ...thread,
    resolution: {
      kind: "eval_spec",
      evalSpecId: input.evalSpecId,
      resolvedBy: input.resolvedBy,
      resolvedAt: input.resolvedAt,
      evidenceRef: input.evidenceRef,
    },
  };
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

export const FIXTURE_THREADS: readonly CommentThread[] = [
  {
    id: "th_refund_escalate",
    anchor: {
      objectId: "node_refund_escalate",
      kind: "flow_node",
      authoredAt: "v34",
    },
    observedAt: "v34",
    comments: [
      {
        id: "cm_1",
        threadId: "th_refund_escalate",
        authorId: "u_amaya",
        authorDisplay: "Amaya O.",
        body: "We should offer callback before transfer for amounts over $200.",
        createdAt: "2025-02-21T10:11:00Z",
        anchor: {
          objectId: "node_refund_escalate",
          kind: "flow_node",
          authoredAt: "v34",
        },
        evidenceRef: "audit/comments/cm_1",
      },
      {
        id: "cm_2",
        threadId: "th_refund_escalate",
        authorId: "u_kojo",
        authorDisplay: "Kojo A.",
        body: "Agreed — let's lock it in via an eval so we don't regress.",
        createdAt: "2025-02-21T10:14:00Z",
        anchor: {
          objectId: "node_refund_escalate",
          kind: "flow_node",
          authoredAt: "v34",
        },
        evidenceRef: "audit/comments/cm_2",
      },
    ],
  },
  {
    id: "th_kb_chunk_callbacks",
    anchor: {
      objectId: "kb_chunk_callbacks",
      kind: "kb_chunk",
      authoredAt: "v9",
    },
    observedAt: "v10",
    comments: [
      {
        id: "cm_3",
        threadId: "th_kb_chunk_callbacks",
        authorId: "u_zara",
        authorDisplay: "Zara N.",
        body: "Callback policy mentions PSTN; verify SMS works in EU.",
        createdAt: "2025-02-20T14:02:00Z",
        anchor: {
          objectId: "kb_chunk_callbacks",
          kind: "kb_chunk",
          authoredAt: "v9",
        },
        evidenceRef: "audit/comments/cm_3",
      },
    ],
  },
];

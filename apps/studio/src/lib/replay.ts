/**
 * Replay / time-travel debugging.
 *
 * A conversation replay is an append-only timeline of events that
 * lets us walk a recorded conversation step-by-step. Each event
 * carries enough state to reconstruct the conversation snapshot at
 * that point in time -- so the studio can rewind, inspect tool
 * calls, and "branch" alternate continuations from any step.
 *
 * Pure data only: this module has no React dependencies.
 */

export type ReplayEventKind =
  | "user_message"
  | "agent_token"
  | "agent_message"
  | "tool_call_start"
  | "tool_call_end"
  | "handoff"
  | "error";

/** Append-only conversation event captured at runtime. */
export type ReplayEvent = {
  /** monotonically increasing index, 0-based. */
  step: number;
  /** wall-clock timestamp, milliseconds since epoch. */
  timestamp_ms: number;
  kind: ReplayEventKind;
  /** Speaker -- "user", agent name, or tool name. */
  actor: string;
  /** Human-readable text payload (may be empty for token deltas). */
  text: string;
  /** Optional structured payload (tool args, error code, etc.). */
  attributes?: Record<string, string | number | boolean>;
};

export type ReplayTrace = {
  id: string;
  conversation_id: string;
  events: ReplayEvent[];
};

/** A coalesced bubble shown at a given replay position. */
export type Bubble = {
  /** Index of the originating event in the source `events` array. */
  source_step: number;
  actor: string;
  /** "user", "agent", "tool", "system". */
  role: "user" | "agent" | "tool" | "system";
  text: string;
};

export type ReplaySnapshot = {
  trace: ReplayTrace;
  /** 0-based event index, clamped to [0, events.length - 1]. */
  cursor: number;
  /** Cumulative bubbles from step 0 up to and including `cursor`. */
  bubbles: Bubble[];
  /** The event at `cursor`, or null when the trace is empty. */
  current: ReplayEvent | null;
};

function roleFor(kind: ReplayEventKind): Bubble["role"] {
  switch (kind) {
    case "user_message":
      return "user";
    case "agent_message":
    case "agent_token":
      return "agent";
    case "tool_call_start":
    case "tool_call_end":
      return "tool";
    case "handoff":
    case "error":
      return "system";
  }
}

/**
 * Reduce a window of events into a tidy bubble list, coalescing
 * streaming agent tokens emitted between two consecutive
 * `agent_message` boundaries into a single transient bubble.
 *
 * Pre-conditions:
 *  - events are sorted by `step` ascending and have unique steps.
 *  - the slice already represents a *prefix* (steps 0..N) so that
 *    the visible state is contiguous.
 */
export function collapseToBubbles(events: ReplayEvent[]): Bubble[] {
  const out: Bubble[] = [];
  let pendingTokens: { actor: string; text: string; step: number } | null = null;

  const flushTokens = () => {
    if (pendingTokens && pendingTokens.text.length > 0) {
      out.push({
        source_step: pendingTokens.step,
        actor: pendingTokens.actor,
        role: "agent",
        text: pendingTokens.text,
      });
    }
    pendingTokens = null;
  };

  for (const event of events) {
    if (event.kind === "agent_token") {
      if (pendingTokens === null || pendingTokens.actor !== event.actor) {
        flushTokens();
        pendingTokens = { actor: event.actor, text: event.text, step: event.step };
      } else {
        pendingTokens.text += event.text;
      }
      continue;
    }
    if (event.kind === "agent_message") {
      // The full message subsumes any partial tokens streamed for it.
      pendingTokens = null;
      out.push({
        source_step: event.step,
        actor: event.actor,
        role: "agent",
        text: event.text,
      });
      continue;
    }
    flushTokens();
    out.push({
      source_step: event.step,
      actor: event.actor,
      role: roleFor(event.kind),
      text: event.text,
    });
  }
  flushTokens();
  return out;
}

/** Compute the snapshot at the given cursor position (clamped). */
export function snapshotAt(trace: ReplayTrace, cursor: number): ReplaySnapshot {
  if (trace.events.length === 0) {
    return {
      trace,
      cursor: 0,
      bubbles: [],
      current: null,
    };
  }
  const last = trace.events.length - 1;
  const clamped = Math.max(0, Math.min(last, Math.floor(cursor)));
  const window = trace.events.slice(0, clamped + 1);
  return {
    trace,
    cursor: clamped,
    bubbles: collapseToBubbles(window),
    current: trace.events[clamped],
  };
}

/** Compute the cursor for the previous user-visible boundary. */
export function previousBoundary(trace: ReplayTrace, cursor: number): number {
  if (trace.events.length === 0) return 0;
  const last = trace.events.length - 1;
  const clamped = Math.max(0, Math.min(last, Math.floor(cursor)));
  for (let i = clamped - 1; i >= 0; i--) {
    const k = trace.events[i].kind;
    if (
      k === "user_message" ||
      k === "agent_message" ||
      k === "tool_call_end" ||
      k === "handoff" ||
      k === "error"
    ) {
      return i;
    }
  }
  return 0;
}

/** Compute the cursor for the next user-visible boundary. */
export function nextBoundary(trace: ReplayTrace, cursor: number): number {
  if (trace.events.length === 0) return 0;
  const last = trace.events.length - 1;
  const clamped = Math.max(0, Math.min(last, Math.floor(cursor)));
  for (let i = clamped + 1; i <= last; i++) {
    const k = trace.events[i].kind;
    if (
      k === "user_message" ||
      k === "agent_message" ||
      k === "tool_call_end" ||
      k === "handoff" ||
      k === "error"
    ) {
      return i;
    }
  }
  return last;
}

/* -------------------------------------------------------------------------
 * Fixture
 * ------------------------------------------------------------------------- */

export const FIXTURE_REPLAY: ReplayTrace = {
  id: "rpl_demo_001",
  conversation_id: "cnv_demo_001",
  events: [
    {
      step: 0,
      timestamp_ms: 1_700_000_000_000,
      kind: "user_message",
      actor: "user",
      text: "Where's my order #1234?",
    },
    {
      step: 1,
      timestamp_ms: 1_700_000_000_400,
      kind: "tool_call_start",
      actor: "lookup_order",
      text: "calling lookup_order",
      attributes: { tool: "lookup_order", order_id: "1234" },
    },
    {
      step: 2,
      timestamp_ms: 1_700_000_000_900,
      kind: "tool_call_end",
      actor: "lookup_order",
      text: "shipped, tracking ABC",
      attributes: { status: "shipped", tracking: "ABC" },
    },
    {
      step: 3,
      timestamp_ms: 1_700_000_001_100,
      kind: "agent_token",
      actor: "support",
      text: "Your ",
    },
    {
      step: 4,
      timestamp_ms: 1_700_000_001_180,
      kind: "agent_token",
      actor: "support",
      text: "order ",
    },
    {
      step: 5,
      timestamp_ms: 1_700_000_001_260,
      kind: "agent_token",
      actor: "support",
      text: "shipped.",
    },
    {
      step: 6,
      timestamp_ms: 1_700_000_001_300,
      kind: "agent_message",
      actor: "support",
      text: "Your order shipped. Tracking: ABC.",
    },
  ],
};

export async function getReplayTrace(id: string): Promise<ReplayTrace | null> {
  if (id === FIXTURE_REPLAY.id) return FIXTURE_REPLAY;
  return null;
}

export const FIXTURE_REPLAY_ID = FIXTURE_REPLAY.id;

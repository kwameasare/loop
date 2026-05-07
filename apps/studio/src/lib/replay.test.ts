import { describe, expect, it } from "vitest";

import {
  FIXTURE_REPLAY,
  buildReplayRequest,
  collapseToBubbles,
  diffReplayTraces,
  nextBoundary,
  previousBoundary,
  replayTraceFromTrace,
  snapshotAt,
} from "./replay";
import type { Trace } from "./traces";

describe("snapshotAt", () => {
  it("clamps the cursor below 0", () => {
    const snap = snapshotAt(FIXTURE_REPLAY, -5);
    expect(snap.cursor).toBe(0);
    expect(snap.current?.kind).toBe("user_message");
  });

  it("clamps the cursor past the end", () => {
    const snap = snapshotAt(FIXTURE_REPLAY, 999);
    expect(snap.cursor).toBe(FIXTURE_REPLAY.events.length - 1);
  });

  it("returns an empty snapshot for an empty trace", () => {
    const snap = snapshotAt(
      { id: "x", conversation_id: "y", events: [] },
      0,
    );
    expect(snap.bubbles).toEqual([]);
    expect(snap.current).toBeNull();
  });

  it("includes only the events up to and including the cursor", () => {
    const snap = snapshotAt(FIXTURE_REPLAY, 2); // through tool_call_end
    expect(snap.bubbles.map((b) => b.role)).toEqual(["user", "tool", "tool"]);
    expect(snap.current?.kind).toBe("tool_call_end");
  });
});

describe("replay run request", () => {
  it("builds the trace detail replay-button payload", () => {
    expect(buildReplayRequest(FIXTURE_REPLAY, "agent-v2")).toEqual({
      trace_id: "rpl_demo_001",
      conversation_id: "cnv_demo_001",
      target_version: "agent-v2",
      frame_count: FIXTURE_REPLAY.events.length,
    });
  });
});

describe("diffReplayTraces", () => {
  it("marks changed, missing, and extra frames for the side-by-side view", () => {
    const actual = {
      ...FIXTURE_REPLAY,
      id: "rpl_demo_002",
      events: [
        FIXTURE_REPLAY.events[0],
        {
          ...FIXTURE_REPLAY.events[1],
          text: "calling lookup_order with retry",
        },
        FIXTURE_REPLAY.events[2],
        FIXTURE_REPLAY.events[3],
        FIXTURE_REPLAY.events[4],
        FIXTURE_REPLAY.events[5],
        FIXTURE_REPLAY.events[6],
        {
          step: 7,
          timestamp_ms: 1_700_000_001_500,
          kind: "error" as const,
          actor: "runtime",
          text: "late warning",
        },
      ],
    };

    const rows = diffReplayTraces(FIXTURE_REPLAY, actual);

    expect(rows[0].status).toBe("same");
    expect(rows[1]).toMatchObject({
      status: "changed",
      color: "amber",
      summary: "text changed",
    });
    expect(rows[7]).toMatchObject({
      status: "extra",
      color: "blue",
      summary: "extra error",
    });

    const missingRows = diffReplayTraces(FIXTURE_REPLAY, {
      ...FIXTURE_REPLAY,
      events: FIXTURE_REPLAY.events.slice(0, 6),
    });
    expect(missingRows[6]).toMatchObject({
      status: "missing",
      color: "red",
      summary: "missing agent_message",
    });
  });
});

describe("collapseToBubbles", () => {
  it("coalesces successive agent tokens into one transient bubble", () => {
    // cursor mid-stream: 3 agent_tokens after the user prompt
    const snap = snapshotAt(FIXTURE_REPLAY, 5);
    const agentBubbles = snap.bubbles.filter((b) => b.role === "agent");
    expect(agentBubbles).toHaveLength(1);
    expect(agentBubbles[0].text).toBe("Your order shipped.");
  });

  it("replaces streamed tokens once the final agent_message arrives", () => {
    const snap = snapshotAt(FIXTURE_REPLAY, 6); // through agent_message
    const agentBubbles = snap.bubbles.filter((b) => b.role === "agent");
    expect(agentBubbles).toHaveLength(1);
    expect(agentBubbles[0].text).toBe("Your order shipped. Tracking: ABC.");
    expect(agentBubbles[0].source_step).toBe(6);
  });

  it("preserves a trailing token bubble when no final message follows", () => {
    const partial = collapseToBubbles(FIXTURE_REPLAY.events.slice(3, 6));
    expect(partial).toHaveLength(1);
    expect(partial[0].text).toBe("Your order shipped.");
  });
});

describe("boundaries", () => {
  it("steps backwards over streamed tokens to the previous boundary", () => {
    // cursor at step 5 (last token); prev boundary should be the
    // tool_call_end at step 2.
    expect(previousBoundary(FIXTURE_REPLAY, 5)).toBe(2);
  });

  it("steps forwards over streamed tokens to the next boundary", () => {
    expect(nextBoundary(FIXTURE_REPLAY, 2)).toBe(6);
  });

  it("clamps at edges", () => {
    expect(previousBoundary(FIXTURE_REPLAY, 0)).toBe(0);
    expect(nextBoundary(FIXTURE_REPLAY, 99)).toBe(
      FIXTURE_REPLAY.events.length - 1,
    );
  });
});

describe("replayTraceFromTrace", () => {
  it("converts a live trace detail into replay events", () => {
    const trace: Trace = {
      id: "abc123",
      summary: {
        outcome: "answered",
        agent_name: "Support",
        environment: "production",
        channel: "web",
        provider: "Runtime",
        model: "recorded",
        deploy_version: "v1",
        snapshot_id: "snap-1",
        total_latency_ns: 25_000_000,
        total_cost_usd: 0,
        tool_count: 1,
        retrieval_count: 0,
        memory_writes: 0,
        eval_score: null,
        eval_suite: null,
      },
      spans: [
        {
          id: "root",
          parent_id: null,
          name: "runtime turn",
          category: "channel",
          kind: "server",
          service: "runtime",
          start_ns: 0,
          end_ns: 10_000_000,
          status: "ok",
          attributes: { conversation_id: "conv-1" },
          events: [],
          input: { user_message: "Where is my order?" },
          output: { outcome: "accepted" },
        },
        {
          id: "tool",
          parent_id: "root",
          name: "tool.lookup_order",
          category: "tool",
          kind: "internal",
          service: "tool-host",
          start_ns: 12_000_000,
          end_ns: 20_000_000,
          status: "ok",
          attributes: { tool: "lookup_order" },
          events: [],
          output: { status: "shipped" },
        },
        {
          id: "answer",
          parent_id: "root",
          name: "llm.answer",
          category: "llm",
          kind: "internal",
          service: "gateway",
          start_ns: 21_000_000,
          end_ns: 25_000_000,
          status: "ok",
          attributes: {},
          events: [],
          output: { answer_summary: "It shipped." },
        },
      ],
    };

    const replay = replayTraceFromTrace(trace);

    expect(replay.conversation_id).toBe("conv-1");
    expect(replay.events.map((event) => event.kind)).toEqual([
      "user_message",
      "handoff",
      "tool_call_start",
      "tool_call_end",
      "agent_message",
    ]);
    expect(replay.events[4].text).toBe("It shipped.");
  });
});

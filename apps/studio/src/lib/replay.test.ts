import { describe, expect, it } from "vitest";

import {
  FIXTURE_REPLAY,
  collapseToBubbles,
  nextBoundary,
  previousBoundary,
  snapshotAt,
} from "./replay";

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

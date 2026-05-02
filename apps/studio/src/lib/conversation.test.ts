import { describe, expect, it } from "vitest";

import {
  appendMessage,
  FIXTURE_TRANSCRIPT,
  type ConversationMessage,
} from "./conversation";

describe("appendMessage", () => {
  it("appends a new message and keeps order ascending", () => {
    const next: ConversationMessage = {
      id: "m4",
      conversation_id: "c",
      role: "operator",
      body: "Hi, I'm here now.",
      created_at_ms: Date.UTC(2026, 4, 1, 11, 57),
    };
    const out = appendMessage(FIXTURE_TRANSCRIPT, next);
    expect(out).toHaveLength(4);
    expect(out[3].id).toBe("m4");
  });

  it("ignores duplicate ids", () => {
    const dup: ConversationMessage = { ...FIXTURE_TRANSCRIPT[1] };
    const out = appendMessage(FIXTURE_TRANSCRIPT, dup);
    expect(out).toHaveLength(FIXTURE_TRANSCRIPT.length);
  });

  it("inserts in chronological order even when delivered out-of-order", () => {
    const old: ConversationMessage = {
      id: "m0",
      conversation_id: "c",
      role: "user",
      body: "earlier message",
      created_at_ms: 1,
    };
    const out = appendMessage(FIXTURE_TRANSCRIPT, old);
    expect(out[0].id).toBe("m0");
  });
});

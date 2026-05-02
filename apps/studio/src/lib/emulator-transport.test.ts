import { describe, expect, it } from "vitest";

import {
  extractTokenText,
  makeFixtureEmulatorTransport,
} from "./emulator-transport";
import type { TurnEvent } from "./sdk-types";

const at = "2025-01-01T00:00:00Z";

describe("makeFixtureEmulatorTransport", () => {
  it("yields seeded events then completes when end() is called", async () => {
    const seed: TurnEvent[] = [
      { type: "token", payload: { text: "Hi" }, ts: at },
      { type: "complete", payload: {}, ts: at },
    ];
    const fx = makeFixtureEmulatorTransport(seed);
    const it = fx.transport
      .start({ agentId: "a1", text: "hello" })
      [Symbol.asyncIterator]();
    const a = await it.next();
    expect(a.done).toBe(false);
    expect((a.value as TurnEvent).type).toBe("token");
    const b = await it.next();
    expect((b.value as TurnEvent).type).toBe("complete");
    fx.end();
    const c = await it.next();
    expect(c.done).toBe(true);
  });

  it("supports push() to extend the stream after start", async () => {
    const fx = makeFixtureEmulatorTransport([]);
    const it = fx.transport
      .start({ agentId: "a1", text: "" })
      [Symbol.asyncIterator]();
    const pending = it.next();
    fx.push({ type: "token", payload: { delta: "ok" }, ts: at });
    const evt = await pending;
    expect((evt.value as TurnEvent).payload).toEqual({ delta: "ok" });
  });
});

describe("extractTokenText", () => {
  it("reads ``text`` and ``delta`` fields from the payload", () => {
    expect(
      extractTokenText({ type: "token", payload: { text: "abc" }, ts: at }),
    ).toBe("abc");
    expect(
      extractTokenText({ type: "token", payload: { delta: "xyz" }, ts: at }),
    ).toBe("xyz");
    expect(
      extractTokenText({ type: "complete", payload: {}, ts: at }),
    ).toBe("");
  });
});

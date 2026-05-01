import { describe, expect, it } from "vitest";

import { lastEventHeaders, nextReconnectState, parseSseText } from "./sse";

describe("parseSseText", () => {
  it("parses JSON data frames with id, event, and retry", () => {
    const frames = parseSseText(
      'id: 41\nevent: turn\ndata: {"type":"token","payload":{"text":"hi"},"ts":"t"}\nretry: 2500\n\n',
    );
    expect(frames).toHaveLength(1);
    expect(frames[0].id).toBe("41");
    expect(frames[0].event).toBe("turn");
    expect(frames[0].retry).toBe(2500);
    expect(frames[0].data).toMatchObject({ type: "token" });
  });

  it("joins multi-line data payloads before decoding", () => {
    const frames = parseSseText("data: hello\ndata: world\n\n", (raw) => raw);
    expect(frames[0].data).toBe("hello\nworld");
  });
});

describe("reconnect state", () => {
  it("tracks Last-Event-Id and retry delay", () => {
    const frames = parseSseText(
      'id: a\ndata: {"x":1}\n\nid: b\ndata: {"x":2}\nretry: 4000\n\n',
    );
    const state = nextReconnectState(frames);
    expect(state).toEqual({ lastEventId: "b", retryMs: 4000 });
    expect(lastEventHeaders(state)).toEqual({ "Last-Event-Id": "b" });
  });
});

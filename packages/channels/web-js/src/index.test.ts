import { describe, expect, it, vi } from "vitest";

import { WebChannelClient, parseSseEvents } from "./index";

function sse(events: object[]): string {
  return events.map((e) => `data: ${JSON.stringify(e)}`).join("\n\n") + "\n\n";
}

describe("parseSseEvents", () => {
  it("parses tokens, tool calls, and complete frames", () => {
    const body = sse([
      { type: "token", text: "Hi" },
      { type: "token", text: " there" },
      { type: "tool_call", name: "search", args: { q: "x" } },
      { type: "tool_result", name: "search", result: { hits: 1 } },
      {
        type: "complete",
        response: { content: [{ type: "text", text: "Hi there" }] },
      },
    ]);
    const events = parseSseEvents(body);
    expect(events).toHaveLength(5);
    expect(events[0]).toEqual({ type: "token", text: "Hi" });
    expect(events[2]).toEqual({
      type: "tool_call",
      name: "search",
      args: { q: "x" },
    });
    expect(events[3]).toEqual({
      type: "tool_result",
      name: "search",
      result: { hits: 1 },
      error: undefined,
    });
    expect(events[4]).toEqual({ type: "complete", text: "Hi there" });
  });

  it("ignores unparseable frames", () => {
    expect(parseSseEvents("data: {bad json\n\n")).toEqual([]);
  });
});

describe("WebChannelClient", () => {
  it("requires baseUrl and agentId", () => {
    expect(
      () => new WebChannelClient({ baseUrl: "", agentId: "a" }),
    ).toThrow();
    expect(
      () => new WebChannelClient({ baseUrl: "https://x", agentId: "" }),
    ).toThrow();
  });

  it("posts the turn body and yields parsed events", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response(
          sse([
            { type: "token", text: "ok" },
            {
              type: "complete",
              response: { content: [{ type: "text", text: "ok" }] },
            },
          ]),
          { status: 200 },
        ),
    );
    const client = new WebChannelClient({
      baseUrl: "https://api.loop.dev/v1",
      agentId: "agt_1",
      conversationId: "conv_x",
      token: "tok_1",
      fetch: fetcher as unknown as typeof fetch,
    });
    const events: unknown[] = [];
    for await (const ev of client.send("hi")) events.push(ev);
    expect(events).toEqual([
      { type: "token", text: "ok" },
      { type: "complete", text: "ok" },
    ]);
    expect(fetcher).toHaveBeenCalledWith(
      "https://api.loop.dev/v1/agents/agt_1/invoke?stream=true",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          accept: "text/event-stream",
          "content-type": "application/json",
          authorization: "Bearer tok_1",
        }),
      }),
    );
    const init = ((fetcher.mock.calls[0] as unknown as unknown[])?.[1] ??
      {}) as RequestInit;
    const body = JSON.parse(String(init.body));
    expect(body).toMatchObject({
      conversation_id: "conv_x",
      user_id: "web-channel",
      channel: "web",
      content: [{ type: "text", text: "hi" }],
    });
  });

  it("yields a single error event on non-2xx responses", async () => {
    const fetcher = vi.fn(
      async () =>
        new Response("nope", {
          status: 500,
          headers: { "x-request-id": "req_zzz" },
        }),
    );
    const client = new WebChannelClient({
      baseUrl: "https://api.loop.dev/v1",
      agentId: "agt_1",
      fetch: fetcher as unknown as typeof fetch,
    });
    const events: unknown[] = [];
    for await (const ev of client.send("hi")) events.push(ev);
    expect(events).toEqual([
      {
        type: "error",
        message: "Loop returned 500",
        status: 500,
        requestId: "req_zzz",
      },
    ]);
  });
});

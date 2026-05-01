/**
 * Integration test for {@link WebChannelClient.connect}: simulates a
 * mid-stream disconnect and verifies that the client reconnects with
 * the most recently observed SSE event id and resumes streaming.
 */
import { describe, it, expect, vi } from "vitest";
import { WebChannelClient, SseParser, computeBackoff } from "./index";

function streamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i >= chunks.length) {
        controller.close();
        return;
      }
      controller.enqueue(enc.encode(chunks[i] ?? ""));
      i += 1;
    },
  });
}

function streamingResponse(chunks: string[]): Response {
  return new Response(streamFromChunks(chunks), {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

describe("connect (auto-reconnect)", () => {
  it("resumes from last-event-id after a mid-stream drop", async () => {
    const calls: { headers: Record<string, string>; body: unknown }[] = [];

    const fetcher = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      const headers: Record<string, string> = {};
      new Headers(init?.headers ?? {}).forEach((v, k) => {
        headers[k] = v;
      });
      calls.push({
        headers,
        body: init?.body ? JSON.parse(String(init.body)) : null,
      });
      if (calls.length === 1) {
        // First connection: emits id:1 and id:2 then closes mid-stream
        // (no `complete` event).
        return streamingResponse([
          'id: 1\ndata: {"type":"token","text":"Hel"}\n\n',
          'id: 2\ndata: {"type":"token","text":"lo"}\n\n',
        ]);
      }
      // Second connection should carry last-event-id=2 and resume.
      return streamingResponse([
        'id: 3\ndata: {"type":"token","text":"!"}\n\n',
        'data: {"type":"complete","response":{"content":[{"type":"text","text":"Hello!"}]}}\n\n',
      ]);
    });

    const client = new WebChannelClient({
      baseUrl: "https://api.example/v1",
      agentId: "agt_test",
      conversationId: "conv_test",
      fetch: fetcher as unknown as typeof fetch,
    });

    const events: { type: string; text?: string }[] = [];
    for await (const ev of client.connect("hi", {
      retry: { initialMs: 0, maxMs: 0, factor: 1, jitter: 0, maxAttempts: 3 },
    })) {
      events.push(ev as { type: string; text?: string });
    }

    expect(events.map((e) => e.type)).toEqual([
      "token",
      "token",
      "token",
      "complete",
    ]);
    expect(events[3]?.text).toBe("Hello!");
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(calls[0]?.headers["last-event-id"]).toBeUndefined();
    expect(calls[1]?.headers["last-event-id"]).toBe("2");
  });

  it("yields error after exhausting retries", async () => {
    const fetcher = vi.fn(async () =>
      streamingResponse(['data: {"type":"token","text":"x"}\n\n']),
    );
    const client = new WebChannelClient({
      baseUrl: "https://api.example/v1",
      agentId: "agt_test",
      conversationId: "conv_test",
      fetch: fetcher as unknown as typeof fetch,
    });
    const events: string[] = [];
    for await (const ev of client.connect("hi", {
      retry: { initialMs: 0, maxMs: 0, factor: 1, jitter: 0, maxAttempts: 1 },
    })) {
      events.push(ev.type);
    }
    expect(events[events.length - 1]).toBe("error");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("invokes onRetry with attempt + delay", async () => {
    const fetcher = vi.fn(async () =>
      streamingResponse([
        'id: 9\ndata: {"type":"token","text":"a"}\n\n',
      ]),
    );
    const client = new WebChannelClient({
      baseUrl: "https://api.example/v1",
      agentId: "agt_test",
      conversationId: "conv_test",
      fetch: fetcher as unknown as typeof fetch,
    });
    const retries: { attempt: number; delayMs: number; lastEventId?: string }[] = [];
    const events: string[] = [];
    for await (const ev of client.connect("hi", {
      retry: { initialMs: 0, maxMs: 0, factor: 1, jitter: 0, maxAttempts: 2 },
      onRetry: (info) => retries.push(info),
    })) {
      events.push(ev.type);
    }
    expect(retries.length).toBe(2);
    expect(retries[0]?.attempt).toBe(1);
    expect(retries[0]?.lastEventId).toBe("9");
  });
});

describe("SseParser", () => {
  it("buffers split chunks across boundaries", () => {
    const p = new SseParser();
    expect(p.feed('id: 1\ndata: {"type":"tok')).toEqual([]);
    expect(p.feed('en","text":"hi"}\n\n')).toEqual([{ type: "token", text: "hi" }]);
    expect(p.lastEventId).toBe("1");
  });

  it("flush drains a trailing block without final newline", () => {
    const p = new SseParser();
    expect(p.feed('data: {"type":"token","text":"a"}')).toEqual([]);
    expect(p.flush()).toEqual([{ type: "token", text: "a" }]);
  });

  it("ignores unknown event types but updates lastEventId", () => {
    const p = new SseParser();
    p.feed('id: 42\ndata: {"type":"heartbeat"}\n\n');
    expect(p.lastEventId).toBe("42");
  });
});

describe("computeBackoff", () => {
  it("grows exponentially capped at maxMs", () => {
    const policy = {
      initialMs: 100,
      maxMs: 800,
      factor: 2,
      jitter: 0,
      maxAttempts: 5,
    };
    expect(computeBackoff(0, policy)).toBe(100);
    expect(computeBackoff(1, policy)).toBe(200);
    expect(computeBackoff(2, policy)).toBe(400);
    expect(computeBackoff(3, policy)).toBe(800);
    expect(computeBackoff(10, policy)).toBe(800);
  });

  it("applies jitter within [1-j, 1+j]", () => {
    const policy = {
      initialMs: 1000,
      maxMs: 1000,
      factor: 1,
      jitter: 0.5,
      maxAttempts: 1,
    };
    expect(computeBackoff(0, policy, () => 0)).toBe(500);
    expect(computeBackoff(0, policy, () => 1)).toBe(1500);
    expect(computeBackoff(0, policy, () => 0.5)).toBe(1000);
  });
});

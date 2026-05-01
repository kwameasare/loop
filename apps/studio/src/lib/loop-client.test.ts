import { describe, expect, it, vi } from "vitest";

import { LoopClient, LoopHttpError } from "./loop-client";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: async () => body,
    text: async () => String(body),
  } as Response;
}

describe("LoopClient", () => {
  it("adds bearer auth and parses json responses", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse(200, { agents: [] }));
    const client = new LoopClient({ baseUrl: "https://api.test/v1/", token: "tok", fetcher });
    await expect(client.request("GET", "/agents")).resolves.toEqual({ agents: [] });
    const [, init] = fetcher.mock.calls[0];
    expect(init.headers.get("authorization")).toBe("Bearer tok");
  });

  it("retries 5xx and honours Retry-After", async () => {
    const sleeps: number[] = [];
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(503, {}, { "Retry-After": "2" }))
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
    const client = new LoopClient({
      baseUrl: "https://api.test/v1",
      fetcher,
      sleep: async (ms) => {
        sleeps.push(ms);
      },
    });
    await expect(client.request("POST", "/deploy", { x: 1 })).resolves.toEqual({ ok: true });
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(sleeps).toEqual([2000]);
  });

  it("throws a typed error after exhausted retries", async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse(503, {}));
    const client = new LoopClient({ baseUrl: "https://api.test/v1", fetcher, sleep: async () => {} });
    await expect(client.request("GET", "/down")).rejects.toBeInstanceOf(LoopHttpError);
    expect(fetcher).toHaveBeenCalledTimes(4);
  });

  it("parses streamed turn frames", async () => {
    const body = 'id: 1\ndata: {"type":"complete","payload":{},"ts":"t"}\n\n';
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      text: async () => body,
    } as Response);
    const client = new LoopClient({ baseUrl: "https://api.test/v1", fetcher });
    const result = await client.invokeTurn("agt_1", {
      channel: "web",
      content: [{ type: "text", text: "hi" }],
      conversation_id: "conv",
      user_id: "u",
    });
    expect(result.frames[0].data.type).toBe("complete");
    expect(result.reconnect.lastEventId).toBe("1");
    expect(fetcher.mock.calls[0][0]).toBe("https://api.test/v1/agents/agt_1/invoke?stream=true");
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { cpJson, cpWebSocketUrl } from "./ux-wireup";

describe("ux wireup cp helpers", () => {
  const original = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = original;
    vi.restoreAllMocks();
  });

  it("joins REST paths under /v1 and posts JSON", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );

    const result = await cpJson("/agents/agt/replay/against-draft", {
      method: "POST",
      body: { trace_ids: ["t1"] },
      fallback: { ok: false },
      fetcher,
      token: "tok",
    });

    expect(result).toEqual({ ok: true });
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.test/v1/agents/agt/replay/against-draft");
    expect(init?.headers).toMatchObject({ authorization: "Bearer tok" });
    expect(JSON.parse(String(init?.body))).toEqual({ trace_ids: ["t1"] });
  });

  it("preserves /v1 when building WebSocket URLs", () => {
    expect(
      cpWebSocketUrl("/workspaces/ws1/presence", {
        baseUrl: "https://cp.test/v1",
        callerSub: "sam@example.com",
      }),
    ).toBe("wss://cp.test/v1/workspaces/ws1/presence?caller_sub=sam%40example.com");
  });
});

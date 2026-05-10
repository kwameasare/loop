import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { __SESSION_STORAGE_KEY_FOR_TESTS__ } from "./cp-auth-exchange";
import { cpJson, cpWebSocketUrl } from "./ux-wireup";

describe("ux wireup cp helpers", () => {
  const original = process.env.LOOP_CP_API_BASE_URL;

  beforeEach(() => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
  });

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = original;
    window.sessionStorage.clear();
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

  it("uses the browser session token for default cpJson calls", async () => {
    window.sessionStorage.setItem(
      __SESSION_STORAGE_KEY_FOR_TESTS__,
      JSON.stringify({
        access_token: "browser-access",
        session_token: "browser-access",
        refresh_token: "browser-refresh",
        expires_in: 3600,
        token_type: "Bearer",
        stored_at: Date.now(),
      }),
    );
    const fetcher = vi.fn<typeof fetch>(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    const result = await cpJson("/workspaces/ws/estate-health", {
      fallback: { ok: false },
    });

    expect(result).toEqual({ ok: true });
    const [url, init] = fetcher.mock.calls[0]!;
    expect(url).toBe("https://cp.test/v1/workspaces/ws/estate-health");
    expect(init?.headers).toMatchObject({
      authorization: "Bearer browser-access",
    });
  });

  it("can require a configured cp-api instead of falling back", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    await expect(
      cpJson("/agents/agt/replay/against-draft", {
        method: "POST",
        body: { trace_ids: ["t1"] },
        fallback: { ok: false },
        allowFallback: false,
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("fails closed by default when cp-api is unconfigured", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    await expect(
      cpJson("/agents/agt/replay/against-draft", {
        fallback: { ok: false },
      }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("uses local fallback only when explicitly allowed", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";

    await expect(
      cpJson("/agents/agt/replay/against-draft", {
        fallback: { ok: false },
        allowFallback: true,
      }),
    ).resolves.toEqual({ ok: false });
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

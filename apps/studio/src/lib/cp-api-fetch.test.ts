/**
 * P0.3: tests for the cp-api 401 interceptor.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  __resetInflightRefreshForTests,
  createAuthedCpApiFetch,
} from "./cp-api-fetch";
import {
  __SESSION_STORAGE_KEY_FOR_TESTS__,
  readSessionToken,
} from "./cp-auth-exchange";

function seedSession(opts: {
  access_token: string;
  refresh_token?: string | null;
}) {
  window.sessionStorage.setItem(
    __SESSION_STORAGE_KEY_FOR_TESTS__,
    JSON.stringify({
      access_token: opts.access_token,
      session_token: opts.access_token,
      refresh_token: opts.refresh_token ?? null,
      expires_in: 3600,
      token_type: "Bearer",
      stored_at: Date.now(),
    }),
  );
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("createAuthedCpApiFetch", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_LOOP_API_URL = "https://cp.test";
    window.sessionStorage.clear();
    __resetInflightRefreshForTests();
  });

  afterEach(() => {
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    vi.restoreAllMocks();
  });

  it("attaches the bearer token from sessionStorage", async () => {
    seedSession({ access_token: "tok-a" });
    const inner = vi.fn().mockResolvedValue(jsonResponse({ ok: true }));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    await f("https://cp.test/v1/agents", { method: "GET" });
    const [, init] = inner.mock.calls[0];
    expect((init.headers as Record<string, string>).authorization).toBe(
      "Bearer tok-a",
    );
  });

  it("on 401 calls /v1/auth/refresh, persists the new token, and retries", async () => {
    seedSession({ access_token: "old-access", refresh_token: "rt-1" });
    const inner = vi
      .fn()
      // First request: 401
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401))
      // /v1/auth/refresh: rotated pair
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-access",
          refresh_token: "rt-2",
          token_type: "Bearer",
          access_expires_at_ms: Date.now() + 3_600_000,
          refresh_expires_at_ms: Date.now() + 30 * 24 * 3_600_000,
        }),
      )
      // Retry of original: 200
      .mockResolvedValueOnce(jsonResponse({ ok: true }));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    const res = await f("https://cp.test/v1/agents", { method: "GET" });
    expect(res.status).toBe(200);
    // First call sent old token; refresh middle; retry sent new token.
    const [, firstInit] = inner.mock.calls[0];
    expect((firstInit.headers as Record<string, string>).authorization).toBe(
      "Bearer old-access",
    );
    const [refreshUrl, refreshInit] = inner.mock.calls[1];
    expect(String(refreshUrl)).toBe("https://cp.test/v1/auth/refresh");
    expect(JSON.parse(String(refreshInit.body))).toEqual({
      refresh_token: "rt-1",
    });
    const [, retryInit] = inner.mock.calls[2];
    expect((retryInit.headers as Record<string, string>).authorization).toBe(
      "Bearer new-access",
    );
    // The rotated refresh token is persisted for the next round.
    const stored = readSessionToken();
    expect(stored?.access_token).toBe("new-access");
    expect(stored?.refresh_token).toBe("rt-2");
  });

  it("returns the original 401 if no refresh token is available", async () => {
    seedSession({ access_token: "old-access", refresh_token: null });
    const inner = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    const res = await f("https://cp.test/v1/agents");
    expect(res.status).toBe(401);
    expect(inner).toHaveBeenCalledTimes(1);
  });

  it("clears the session on a 401 from /v1/auth/refresh (reuse detection)", async () => {
    seedSession({ access_token: "old-access", refresh_token: "rt-stolen" });
    const inner = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: "reuse" }, 401));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    const res = await f("https://cp.test/v1/agents");
    expect(res.status).toBe(401);
    expect(readSessionToken()).toBeNull();
  });

  it("does not retry non-401 responses", async () => {
    seedSession({ access_token: "tok-a", refresh_token: "rt-1" });
    const inner = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ error: "boom" }, 500));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    const res = await f("https://cp.test/v1/agents");
    expect(res.status).toBe(500);
    expect(inner).toHaveBeenCalledTimes(1);
  });

  it("coalesces concurrent 401s to a single refresh round-trip", async () => {
    seedSession({ access_token: "old-access", refresh_token: "rt-1" });
    const inner = vi
      .fn()
      // Two concurrent calls each get a 401.
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401))
      .mockResolvedValueOnce(jsonResponse({ error: "expired" }, 401))
      // Refresh round-trip (must only happen once).
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new-access",
          refresh_token: "rt-2",
          token_type: "Bearer",
        }),
      )
      // Retries.
      .mockResolvedValueOnce(jsonResponse({ ok: 1 }))
      .mockResolvedValueOnce(jsonResponse({ ok: 2 }));
    const f = createAuthedCpApiFetch({ fetcher: inner as never });
    const [res1, res2] = await Promise.all([
      f("https://cp.test/v1/agents/a"),
      f("https://cp.test/v1/agents/b"),
    ]);
    expect(res1.status).toBe(200);
    expect(res2.status).toBe(200);
    // 2 originals + 1 refresh + 2 retries = 5 calls.
    expect(inner).toHaveBeenCalledTimes(5);
    const refreshCalls = inner.mock.calls.filter(([url]) =>
      String(url).endsWith("/v1/auth/refresh"),
    );
    expect(refreshCalls).toHaveLength(1);
  });
});

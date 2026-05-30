/**
 * Tests for the /api/session Route Handler — the BFF that proxies
 * Auth0 ID-token → cp /v1/auth/exchange and sets HttpOnly
 * session cookies for SSR auth.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST, DELETE } from "./route";

const originalFetch = globalThis.fetch;

beforeEach(() => {
  process.env.LOOP_CP_API_BASE_URL = "https://cp.example.test";
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  delete process.env.LOOP_CP_API_BASE_URL;
});

function makeRequest(body: unknown): Request {
  return new Request("http://localhost/api/session", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/session", () => {
  it("rejects missing id_token with 400", async () => {
    const response = await POST(makeRequest({}));
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toMatch(/id_token/);
  });

  it("forwards id_token to cp and sets HttpOnly access + refresh cookies", async () => {
    let capturedUrl: string | URL | undefined;
    let capturedInit: RequestInit | undefined;
    globalThis.fetch = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        capturedUrl = input as string | URL;
        capturedInit = init;
        return new Response(
          JSON.stringify({
            access_token: "v4.local.access",
            refresh_token: "refresh-opaque",
            token_type: "Bearer",
            access_expires_at_ms: Date.now() + 3600_000,
            refresh_expires_at_ms: Date.now() + 30 * 24 * 3600_000,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      },
    ) as typeof fetch;

    const response = await POST(
      makeRequest({ id_token: "id-token-from-auth0" }),
    );
    expect(response.status).toBe(200);
    expect(String(capturedUrl)).toBe(
      "https://cp.example.test/v1/auth/exchange",
    );
    expect(JSON.parse(String(capturedInit?.body))).toEqual({
      id_token: "id-token-from-auth0",
    });
    const setCookieHeaders = response.headers.getSetCookie();
    const accessCookie = setCookieHeaders.find((c) =>
      c.startsWith("loop.cp.access="),
    );
    const refreshCookie = setCookieHeaders.find((c) =>
      c.startsWith("loop.cp.refresh="),
    );
    expect(accessCookie).toBeDefined();
    expect(accessCookie).toMatch(/HttpOnly/i);
    expect(accessCookie).toMatch(/SameSite=lax/i);
    expect(accessCookie).toMatch(/v4\.local\.access/);
    expect(refreshCookie).toBeDefined();
    expect(refreshCookie).toMatch(/HttpOnly/i);
    expect(refreshCookie).toMatch(/refresh-opaque/);
    // Body still returns the tokens so client-side code can mirror
    // them into sessionStorage (transitional path).
    const body = await response.json();
    expect(body.access_token).toBe("v4.local.access");
  });

  it("surfaces 502 with cp body when /v1/auth/exchange fails", async () => {
    globalThis.fetch = vi.fn(
      async () =>
        new Response("invalid signature", {
          status: 401,
          headers: { "content-type": "text/plain" },
        }),
    ) as typeof fetch;
    const response = await POST(
      makeRequest({ id_token: "broken-id-token-from-auth0" }),
    );
    expect(response.status).toBe(502);
    const body = await response.json();
    expect(body.error).toMatch(/HTTP 401/);
    expect(body.upstream_body).toContain("invalid signature");
  });
});

describe("DELETE /api/session", () => {
  it("clears both cookies", async () => {
    const response = await DELETE();
    expect(response.status).toBe(200);
    const setCookieHeaders = response.headers.getSetCookie();
    const accessCookie = setCookieHeaders.find((c) =>
      c.startsWith("loop.cp.access="),
    );
    const refreshCookie = setCookieHeaders.find((c) =>
      c.startsWith("loop.cp.refresh="),
    );
    expect(accessCookie).toMatch(/Max-Age=0/i);
    expect(refreshCookie).toMatch(/Max-Age=0/i);
  });
});

/**
 * S912: tests for the cp-api ``/v1/auth/exchange`` helper.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  AuthExchangeError,
  __SESSION_STORAGE_KEY_FOR_TESTS__,
  clearSessionToken,
  exchangeAuth0Token,
  readSessionToken,
  storeSessionToken,
} from "@/lib/cp-auth-exchange";

describe("exchangeAuth0Token", () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_LOOP_API_URL = "https://cp.example.test";
    window.sessionStorage.clear();
  });
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
  });

  it("posts the id_token to /v1/auth/exchange and returns the session", async () => {
    const fetcher = vi.fn(async (url, init) => {
      expect(url).toBe("https://cp.example.test/v1/auth/exchange");
      expect(init?.method).toBe("POST");
      expect(JSON.parse(String(init?.body))).toEqual({
        id_token: "eyJ.fake.token",
      });
      expect(
        (init?.headers as Record<string, string>)["Content-Type"]
      ).toBe("application/json");
      return new Response(
        JSON.stringify({
          access_token: "loop-session-abc",
          token_type: "Bearer",
          expires_in: 3600,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    });
    const result = await exchangeAuth0Token("eyJ.fake.token", { fetcher });
    expect(result.access_token).toBe("loop-session-abc");
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("strips trailing slashes from the base url", async () => {
    const fetcher = vi.fn(async (url) => {
      expect(url).toBe("https://cp.trail.test/v1/auth/exchange");
      return new Response(JSON.stringify({ access_token: "x" }), {
        status: 200,
      });
    });
    await exchangeAuth0Token("tok", {
      baseUrl: "https://cp.trail.test/",
      fetcher,
    });
  });

  it("throws AuthExchangeError on a 4xx response", async () => {
    const fetcher = vi.fn(
      async () => new Response("denied", { status: 401 })
    );
    await expect(
      exchangeAuth0Token("tok", { fetcher })
    ).rejects.toBeInstanceOf(AuthExchangeError);
    await expect(
      exchangeAuth0Token("tok", { fetcher })
    ).rejects.toMatchObject({ status: 401, body: "denied" });
  });

  it("throws AuthExchangeError on a non-JSON body", async () => {
    const fetcher = vi.fn(async () => new Response("<html/>", { status: 200 }));
    await expect(
      exchangeAuth0Token("tok", { fetcher })
    ).rejects.toBeInstanceOf(AuthExchangeError);
  });

  it("throws when no base url is configured", async () => {
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
    await expect(
      exchangeAuth0Token("tok", { fetcher: vi.fn() })
    ).rejects.toThrow(/NEXT_PUBLIC_LOOP_API_URL/);
  });
});

describe("session token storage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("stores and reads back a session token", () => {
    storeSessionToken({
      access_token: "tok-1",
      session_token: "sess-1",
      token_type: "Bearer",
      expires_in: 600,
    });
    const raw = window.sessionStorage.getItem(
      __SESSION_STORAGE_KEY_FOR_TESTS__
    );
    expect(raw).not.toBeNull();
    const parsed = readSessionToken();
    expect(parsed?.access_token).toBe("tok-1");
    expect(parsed?.session_token).toBe("sess-1");
    expect(parsed?.token_type).toBe("Bearer");
    expect(parsed?.expires_in).toBe(600);
  });

  it("falls back to access_token when session_token is absent", () => {
    storeSessionToken({ access_token: "only-access" });
    expect(readSessionToken()?.session_token).toBe("only-access");
  });

  it("clearSessionToken removes the entry", () => {
    storeSessionToken({ access_token: "tok" });
    clearSessionToken();
    expect(readSessionToken()).toBeNull();
  });

  it("readSessionToken returns null when storage is empty or invalid", () => {
    expect(readSessionToken()).toBeNull();
    window.sessionStorage.setItem(
      __SESSION_STORAGE_KEY_FOR_TESTS__,
      "not-json"
    );
    expect(readSessionToken()).toBeNull();
  });
});

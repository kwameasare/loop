/**
 * S912: integration-style test for the Auth0 callback page.
 *
 * The page is wrapped in our auth0 mock (returning an authenticated
 * user) and a stub ``fetch`` that captures the POST to
 * ``/v1/auth/exchange``. We verify the page calls ``router.replace``
 * after a successful exchange.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const replace = vi.fn();
const getIdTokenClaims = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@auth0/auth0-react", () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth0: () => ({
    getIdTokenClaims,
    isAuthenticated: true,
    isLoading: false,
    user: { sub: "auth0|abc", email: "u@example.test" },
  }),
}));

vi.mock("@/lib/use-user", () => ({
  useUser: () => ({
    user: { sub: "auth0|abc", email: "u@example.test" },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

import AuthCallbackPage from "@/app/auth/callback/page";

describe("AuthCallbackPage", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_LOOP_API_URL = "https://cp.example.test";
    replace.mockReset();
    getIdTokenClaims.mockReset();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    delete process.env.NEXT_PUBLIC_LOOP_API_URL;
  });

  it("exchanges the id_token, stores the session, and redirects home", async () => {
    getIdTokenClaims.mockResolvedValue({ __raw: "id-token-from-auth0" });
    const fetchSpy = vi.fn(async (url, init) => {
      expect(url).toBe("https://cp.example.test/v1/auth/exchange");
      expect(JSON.parse(String(init?.body))).toEqual({
        id_token: "id-token-from-auth0",
      });
      return new Response(
        JSON.stringify({
          access_token: "loop-session-xyz",
          session_token: "loop-session-xyz",
          token_type: "Bearer",
          expires_in: 1800,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    });
    globalThis.fetch = fetchSpy as typeof fetch;

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/");
    });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const stored = window.sessionStorage.getItem("loop.cp.session");
    expect(stored).toContain("loop-session-xyz");
  });

  it("renders an error when cp-api rejects the exchange", async () => {
    getIdTokenClaims.mockResolvedValue({ __raw: "id-token-from-auth0" });
    globalThis.fetch = vi.fn(
      async () => new Response("forbidden", { status: 403 })
    ) as typeof fetch;

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders an error when Auth0 returns no id_token", async () => {
    getIdTokenClaims.mockResolvedValue(undefined);
    globalThis.fetch = vi.fn() as typeof fetch;

    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(screen.getByTestId("auth-error")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });
});

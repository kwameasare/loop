import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { __SESSION_STORAGE_KEY_FOR_TESTS__ } from "@/lib/cp-auth-exchange";

const auth0State = {
  user: {
    sub: "auth0|user-123",
    email: "user@example.com",
    name: "Sample User",
  },
  isAuthenticated: true,
  isLoading: false,
};

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => auth0State,
}));

import { useUser } from "@/lib/use-user";

describe("useUser", () => {
  beforeEach(() => {
    auth0State.isAuthenticated = true;
    auth0State.isLoading = false;
    auth0State.user = {
      sub: "auth0|user-123",
      email: "user@example.com",
      name: "Sample User",
    };
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns the identity when Auth0 reports an authenticated user", () => {
    vi.stubEnv("NEXT_PUBLIC_AUTH0_DOMAIN", "example.auth0.com");
    const { result } = renderHook(() => useUser());
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.sub).toBe("auth0|user-123");
    expect(result.current.user?.email).toBe("user@example.com");
  });

  it("uses the mirrored Loop session after an Auth0-backed reload", async () => {
    vi.stubEnv("NEXT_PUBLIC_AUTH0_DOMAIN", "example.auth0.com");
    auth0State.isAuthenticated = false;
    auth0State.isLoading = true;
    auth0State.user = null as unknown as typeof auth0State.user;
    window.sessionStorage.setItem(
      __SESSION_STORAGE_KEY_FOR_TESTS__,
      JSON.stringify({
        access_token: "opaque.loop.session",
        session_token: "opaque.loop.session",
        refresh_token: "refresh-loop-session",
        token_type: "Bearer",
        expires_in: 1800,
        stored_at: Date.now(),
      }),
    );

    const { result } = renderHook(() => useUser());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.sub).toBe("dev-pilot");
  });

  it("uses the local Loop session only when Auth0 is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_AUTH0_DOMAIN", "");
    auth0State.isAuthenticated = false;
    auth0State.isLoading = true;
    auth0State.user = null as unknown as typeof auth0State.user;
    window.sessionStorage.setItem(
      __SESSION_STORAGE_KEY_FOR_TESTS__,
      JSON.stringify({
        access_token: "opaque.loop.session",
        session_token: "opaque.loop.session",
        refresh_token: "refresh-loop-session",
        token_type: "Bearer",
        expires_in: 1800,
        stored_at: Date.now(),
      }),
    );

    const { result } = renderHook(() => useUser());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.sub).toBe("dev-pilot");
  });
});

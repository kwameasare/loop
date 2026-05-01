import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";

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
  it("returns the identity when Auth0 reports an authenticated user", () => {
    const { result } = renderHook(() => useUser());
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user?.sub).toBe("auth0|user-123");
    expect(result.current.user?.email).toBe("user@example.com");
  });
});

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const replace = vi.fn();
const pathname = "/agents";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn(), forward: vi.fn() }),
  usePathname: () => pathname,
  useSearchParams: () => new URLSearchParams(),
}));

const userState = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
};

vi.mock("@/lib/use-user", () => ({
  useUser: () => userState,
}));

import { RequireAuth } from "@/components/auth/require-auth";

describe("RequireAuth", () => {
  beforeEach(() => {
    replace.mockReset();
    userState.isAuthenticated = false;
    userState.isLoading = false;
  });

  it("redirects unauthenticated users to /login with returnTo", async () => {
    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/login?returnTo=%2Fagents"),
    );
    expect(screen.queryByText("secret")).not.toBeInTheDocument();
  });

  it("renders children when authenticated", () => {
    userState.isAuthenticated = true;
    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );
    expect(screen.getByText("secret")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders the placeholder while Auth0 is still loading", () => {
    userState.isLoading = true;
    render(
      <RequireAuth>
        <p>secret</p>
      </RequireAuth>,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});

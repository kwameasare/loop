import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

const loginWithRedirect = vi.fn();

vi.mock("@auth0/auth0-react", () => ({
  Auth0Provider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useAuth0: () => ({
    loginWithRedirect,
    logout: vi.fn(),
    isLoading: false,
    isAuthenticated: false,
    user: undefined,
  }),
}));

import { SignInButton } from "@/components/auth/sign-in-button";

describe("SignInButton", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    loginWithRedirect.mockClear();
  });

  it("triggers loginWithRedirect when clicked", () => {
    vi.stubEnv("NEXT_PUBLIC_AUTH0_DOMAIN", "example.auth0.com");
    render(<SignInButton />);
    fireEvent.click(screen.getByTestId("sign-in-button"));
    expect(loginWithRedirect).toHaveBeenCalledTimes(1);
  });
});

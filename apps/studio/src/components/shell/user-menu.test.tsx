import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const userState: {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: { sub: string; email: string; name?: string } | null;
} = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
};

vi.mock("@/lib/use-user", () => ({
  useUser: () => userState,
}));

vi.mock("@auth0/auth0-react", () => ({
  useAuth0: () => ({
    logout: vi.fn(),
  }),
}));

import { UserMenu } from "@/components/shell/user-menu";

describe("UserMenu", () => {
  beforeEach(() => {
    userState.isAuthenticated = false;
    userState.user = null;
  });

  it("renders nothing when the visitor is anonymous", () => {
    const { container } = render(<UserMenu />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the avatar initial and display name when signed in", () => {
    userState.isAuthenticated = true;
    userState.user = { sub: "u1", email: "ada@example.com", name: "Ada Lovelace" };
    render(<UserMenu />);
    expect(screen.getByTestId("user-display")).toHaveTextContent("Ada Lovelace");
    expect(screen.getByTestId("sign-out-button")).toBeInTheDocument();
  });
});

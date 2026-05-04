import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-user", () => ({
  useUser: vi.fn(),
}));

vi.mock("./members-screen", () => ({
  MembersScreen: ({
    workspaceId,
    currentUserSub,
  }: {
    workspaceId: string;
    currentUserSub: string;
  }) => (
    <div data-testid="members-screen-props">
      {workspaceId}:{currentUserSub}
    </div>
  ),
}));

import { useUser } from "@/lib/use-user";
import MembersPage from "./page";

const mockedUseUser = vi.mocked(useUser);

describe("MembersPage", () => {
  it("passes workspace id and current user sub to MembersScreen", () => {
    mockedUseUser.mockReturnValue({
      user: { sub: "user-123" },
      isAuthenticated: true,
      isLoading: false,
    });

    render(<MembersPage params={{ workspace_id: "ws_1" }} />);

    expect(screen.getByTestId("members-screen-props")).toHaveTextContent(
      "ws_1:user-123",
    );
  });

  it("shows sign-in hint when user is unavailable", () => {
    mockedUseUser.mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });

    render(<MembersPage params={{ workspace_id: "ws_1" }} />);

    expect(screen.getByText(/Sign in to view workspace members/)).toBeInTheDocument();
  });
});

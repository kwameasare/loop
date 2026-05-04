import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: vi.fn(),
}));

import { useActiveWorkspace } from "@/lib/use-active-workspace";
import { WorkspaceMembersLink } from "@/components/shell/workspace-members-link";

const mockedUseActiveWorkspace = vi.mocked(useActiveWorkspace);

describe("WorkspaceMembersLink", () => {
  it("renders a link for the active workspace", () => {
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: { id: "ws_acme", name: "Acme", slug: "acme", role: "owner" },
      isLoading: false,
      setActive: vi.fn(),
    });

    render(<WorkspaceMembersLink />);

    const link = screen.getByTestId("workspace-members-link");
    expect(link).toHaveAttribute("href", "/workspaces/ws_acme/members");
  });

  it("does not render while loading", () => {
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: null,
      isLoading: true,
      setActive: vi.fn(),
    });

    render(<WorkspaceMembersLink />);

    expect(screen.queryByTestId("workspace-members-link")).toBeNull();
  });
});

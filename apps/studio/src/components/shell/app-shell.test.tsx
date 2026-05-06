import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/agents",
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/shell/workspace-switcher", () => ({
  WorkspaceSwitcher: () => <span>Acme Support Ops</span>,
}));

vi.mock("@/components/shell/workspace-members-link", () => ({
  WorkspaceMembersLink: () => <a href="/workspaces/enterprise">Members</a>,
}));

vi.mock("@/components/shell/user-menu", () => ({
  UserMenu: () => <span>User menu</span>,
}));

import { AppShell } from "@/components/shell/app-shell";

describe("AppShell", () => {
  it("mounts the canonical five-region Studio layout", () => {
    render(
      <AppShell>
        <div>Workbench content</div>
      </AppShell>,
    );

    expect(screen.getByTestId("asset-rail")).toBeInTheDocument();
    expect(screen.getByTestId("topbar")).toBeInTheDocument();
    expect(screen.getByTestId("work-surface")).toHaveTextContent(
      "Workbench content",
    );
    expect(screen.getByTestId("live-preview-rail")).toBeInTheDocument();
    expect(screen.getByTestId("activity-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("status-footer")).toBeInTheDocument();
  });
});

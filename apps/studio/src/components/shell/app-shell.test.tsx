import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/agents",
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
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

vi.mock("@/components/shell/activity-ribbon", () => ({
  ActivityRibbon: () => <div data-testid="workspace-activity-ribbon" />,
}));

vi.mock("@/components/shell/user-menu", () => ({
  UserMenu: () => <span>User menu</span>,
}));

vi.mock("@/components/help", () => ({
  HelpClipLauncher: () => <button type="button">Help</button>,
  TelemetryConsentGate: () => <div data-testid="telemetry-consent-gate" />,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: null,
    isLoading: false,
    workspaces: [],
    setActive: vi.fn(),
  }),
}));

vi.mock("@/lib/use-user", () => ({
  useUser: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
  }),
}));

vi.mock("@/lib/use-presence-socket", () => ({
  usePresenceSocket: () => ({
    connected: false,
    error: null,
    socketUrl: null,
    users: [],
  }),
}));

import { AppShell } from "@/components/shell/app-shell";

describe("AppShell", () => {
  it("mounts the disciplined Studio shell without global live fixtures", () => {
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
    expect(screen.queryByTestId("live-preview-rail")).not.toBeInTheDocument();
    expect(screen.queryByTestId("activity-timeline")).not.toBeInTheDocument();
    expect(screen.queryByTestId("status-footer")).not.toBeInTheDocument();
    expect(screen.getByTestId("telemetry-consent-gate")).toBeInTheDocument();
  });
});

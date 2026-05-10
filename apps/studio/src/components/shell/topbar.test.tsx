import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  pathname: "/agents/agent_1/behavior",
  usePresenceSocket: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => mocks.pathname,
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

vi.mock("@/components/command", () => ({
  CommandPaletteLauncher: () => <button type="button">Command</button>,
}));

vi.mock("@/components/help", () => ({
  HelpClipLauncher: () => <button type="button">Help</button>,
}));

vi.mock("@/components/shell/activity-ribbon", () => ({
  ActivityRibbon: () => <div data-testid="workspace-activity-ribbon" />,
}));

vi.mock("@/components/shell/theme-toggle", () => ({
  ThemeToggle: () => <button type="button">Theme</button>,
}));

vi.mock("@/components/shell/user-menu", () => ({
  UserMenu: () => <button type="button">User</button>,
}));

vi.mock("@/components/shell/workspace-switcher", () => ({
  WorkspaceSwitcher: () => <span>Acme Workspace</span>,
}));

vi.mock("@/components/collaboration/pair-debug-audio-control", () => ({
  PairDebugAudioControl: ({
    workspaceId,
    agentId,
    teammateCount,
    participantId,
  }: {
    workspaceId: string;
    agentId: string;
    teammateCount: number;
    participantId?: string;
  }) => (
    <div data-testid="pair-debug-audio-control">
      {workspaceId}:{agentId}:{teammateCount}:{participantId}
    </div>
  ),
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_1", name: "Acme", slug: "acme", role: "owner" },
    isLoading: false,
    workspaces: [],
    setActive: vi.fn(),
  }),
}));

vi.mock("@/lib/use-user", () => ({
  useUser: () => ({
    user: {
      sub: "builder:sam",
      email: "sam@example.com",
      name: "Sam",
    },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("@/lib/use-presence-socket", () => ({
  usePresenceSocket: (...args: unknown[]) => mocks.usePresenceSocket(...args),
}));

import { Topbar } from "@/components/shell/topbar";

describe("Topbar", () => {
  beforeEach(() => {
    mocks.pathname = "/agents/agent_1/behavior";
    mocks.usePresenceSocket.mockReturnValue({
      connected: true,
      error: null,
      socketUrl: "wss://cp.test/v1/workspaces/ws_1/presence",
      users: [
        {
          id: "builder:sam",
          display: "Sam",
          color: "var(--trace-server)",
          status: "active",
          focus: "agent/agent_1",
        },
        {
          id: "builder:maya",
          display: "Maya",
          color: "var(--trace-client)",
          status: "active",
          focus: "agent/agent_1",
        },
      ],
    });
  });

  it("mounts pair-debug audio in the agent topbar when a teammate is present", () => {
    render(<Topbar />);

    expect(screen.getByTestId("topbar-pair-debug-audio")).toBeInTheDocument();
    expect(screen.getByTestId("pair-debug-audio-control")).toHaveTextContent(
      "ws_1:agent_1:1:builder:sam",
    );
    expect(mocks.usePresenceSocket).toHaveBeenCalledWith(
      expect.objectContaining({
        workspaceId: "ws_1",
        callerSub: "builder:sam",
        display: "Sam",
        focus: "agent/agent_1",
        enabled: true,
      }),
    );
  });

  it("does not show pair-debug audio on estate routes", () => {
    mocks.pathname = "/observe";

    render(<Topbar />);

    expect(
      screen.queryByTestId("topbar-pair-debug-audio"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("pair-debug-audio-control"),
    ).not.toBeInTheDocument();
    expect(mocks.usePresenceSocket).toHaveBeenCalledWith(
      expect.objectContaining({
        workspaceId: undefined,
        enabled: false,
      }),
    );
  });

  it("does not show pair-debug audio when no teammate shares the agent focus", () => {
    mocks.usePresenceSocket.mockReturnValue({
      connected: true,
      error: null,
      socketUrl: "wss://cp.test/v1/workspaces/ws_1/presence",
      users: [
        {
          id: "builder:sam",
          display: "Sam",
          color: "var(--trace-server)",
          status: "active",
          focus: "agent/agent_1",
        },
        {
          id: "builder:maya",
          display: "Maya",
          color: "var(--trace-client)",
          status: "active",
          focus: "agent/agent_2",
        },
      ],
    });

    render(<Topbar />);

    expect(
      screen.queryByTestId("topbar-pair-debug-audio"),
    ).not.toBeInTheDocument();
  });
});

import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import type { MockedFunction } from "vitest";

const replace = vi.fn();
const params = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace,
    push: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  usePathname: () => "/agents",
  useSearchParams: () => params,
}));

vi.mock("@/lib/workspaces", () => ({
  listWorkspaces: vi.fn(),
}));

import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";
import { listWorkspaces } from "@/lib/workspaces";

const mockedListWorkspaces = listWorkspaces as MockedFunction<
  typeof listWorkspaces
>;

const WORKSPACES = [
  {
    id: "ws_acme",
    name: "Acme Live",
    slug: "acme-live",
    role: "owner" as const,
  },
  {
    id: "ws_bank",
    name: "Bank Ops",
    slug: "bank-ops",
    role: "admin" as const,
  },
];

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    replace.mockReset();
    mockedListWorkspaces.mockReset();
    mockedListWorkspaces.mockResolvedValue({ workspaces: WORKSPACES });
    window.localStorage.clear();
    params.delete("ws");
  });

  it("does not render a fixture workspace when no authorized workspace exists", async () => {
    mockedListWorkspaces.mockResolvedValue({ workspaces: [] });
    render(<WorkspaceSwitcher />);
    await waitFor(() => {
      expect(
        screen.queryByTestId("workspace-switcher-loading"),
      ).not.toBeInTheDocument();
      expect(screen.queryByTestId("workspace-switcher")).not.toBeInTheDocument();
    });
  });

  it("renders degraded workspace state when the control plane reports it", async () => {
    mockedListWorkspaces.mockResolvedValue({
      workspaces: [],
      degraded_reason: "Workspace context requires cp-api.",
    });
    render(<WorkspaceSwitcher />);

    expect(
      await screen.findByTestId("workspace-switcher-degraded"),
    ).toHaveTextContent("Workspace unavailable");
    expect(screen.getByTestId("workspace-switcher-degraded")).toHaveAttribute(
      "title",
      "Workspace context requires cp-api.",
    );
  });

  it("renders degraded workspace state when workspace loading rejects", async () => {
    mockedListWorkspaces.mockRejectedValue(
      new Error("cp-api GET workspaces -> 503"),
    );
    render(<WorkspaceSwitcher />);

    expect(
      await screen.findByTestId("workspace-switcher-degraded"),
    ).toHaveAttribute("title", "cp-api GET workspaces -> 503");
  });

  it("renders authorized workspaces from the control plane", async () => {
    params.set("ws", "acme-live");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    expect(select.value).toBe("acme-live");
    expect(select.querySelectorAll("option")).toHaveLength(2);
  });

  it("updates the URL and localStorage when the user changes workspace", async () => {
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "bank-ops" } });
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(expect.stringContaining("ws=bank-ops")),
    );
    expect(window.localStorage.getItem("loop:active-workspace")).toBe(
      "bank-ops",
    );
  });

  it("updates active workspace when another tab writes storage", async () => {
    params.delete("ws");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;

    expect(select.value).toBe("acme-live");

    fireEvent(
      window,
      new StorageEvent("storage", {
        key: "loop:active-workspace",
        newValue: "bank-ops",
      }),
    );

    await waitFor(() => {
      expect(select.value).toBe("bank-ops");
    });
  });
});

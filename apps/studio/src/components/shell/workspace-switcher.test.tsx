import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

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

import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    replace.mockReset();
    window.localStorage.clear();
  });

  it("renders the honest local fallback workspace", async () => {
    params.set("ws", "local");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    expect(select.value).toBe("local");
    expect(select.querySelectorAll("option")).toHaveLength(1);
  });

  it("updates the URL and localStorage when the user confirms the local workspace", async () => {
    params.delete("ws");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "local" } });
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(expect.stringContaining("ws=local")),
    );
    expect(window.localStorage.getItem("loop:active-workspace")).toBe("local");
  });

  it("updates active workspace when another tab writes storage", async () => {
    params.delete("ws");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;

    expect(select.value).toBe("local");

    fireEvent(
      window,
      new StorageEvent("storage", {
        key: "loop:active-workspace",
        newValue: "local",
      }),
    );

    await waitFor(() => {
      expect(select.value).toBe("local");
    });
  });
});

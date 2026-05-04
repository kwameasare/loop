import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const replace = vi.fn();
const params = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn(), forward: vi.fn() }),
  usePathname: () => "/agents",
  useSearchParams: () => params,
}));

import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";

describe("WorkspaceSwitcher", () => {
  beforeEach(() => {
    replace.mockReset();
    window.localStorage.clear();
  });

  it("renders one option per workspace and reflects the URL ?ws", async () => {
    params.set("ws", "globex");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    expect(select.value).toBe("globex");
    expect(select.querySelectorAll("option")).toHaveLength(2);
  });

  it("updates the URL and localStorage when the user picks a workspace", async () => {
    params.delete("ws");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "globex" } });
    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith(expect.stringContaining("ws=globex")),
    );
    expect(window.localStorage.getItem("loop:active-workspace")).toBe("globex");
  });

  it("updates active workspace when another tab writes storage", async () => {
    params.delete("ws");
    render(<WorkspaceSwitcher />);
    const select = (await screen.findByTestId(
      "workspace-switcher-select",
    )) as HTMLSelectElement;

    expect(select.value).toBe("acme");

    fireEvent(
      window,
      new StorageEvent("storage", {
        key: "loop:active-workspace",
        newValue: "globex",
      }),
    );

    await waitFor(() => {
      expect(select.value).toBe("globex");
    });
  });
});

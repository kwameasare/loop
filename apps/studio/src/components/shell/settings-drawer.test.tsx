import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

vi.mock("@/lib/regions", () => ({
  inferRegion: () => "eu-west" as const,
}));

// Stub localStorage
const localStorageStore: Record<string, string> = {};
const localStorageMock = {
  getItem: (k: string) => localStorageStore[k] ?? null,
  setItem: (k: string, v: string) => {
    localStorageStore[k] = v;
  },
  removeItem: (k: string) => {
    delete localStorageStore[k];
  },
  clear: () => {
    for (const k of Object.keys(localStorageStore)) delete localStorageStore[k];
  },
};
Object.defineProperty(globalThis, "localStorage", {
  value: localStorageMock,
  writable: true,
});

import { SettingsDrawer, SettingsButton } from "@/components/shell/settings-drawer";

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("SettingsDrawer", () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  afterEach(() => {
    localStorageMock.clear();
  });

  it("renders nothing when closed", () => {
    const { container } = render(
      <SettingsDrawer open={false} onClose={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the drawer panel when open", () => {
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    expect(screen.getByTestId("settings-drawer")).toBeInTheDocument();
  });

  it("shows profile name input with default value", () => {
    render(
      <SettingsDrawer open={true} onClose={() => {}} defaultProfileName="Ada" />,
    );
    const input = screen.getByTestId("settings-profile-name-input") as HTMLInputElement;
    expect(input.value).toBe("Ada");
  });

  it("allows editing profile name and saving", () => {
    render(
      <SettingsDrawer open={true} onClose={() => {}} defaultProfileName="Ada" />,
    );
    const input = screen.getByTestId("settings-profile-name-input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Charles" } });
    fireEvent.click(screen.getByTestId("settings-profile-name-save"));
    // localStorage should be updated
    expect(localStorageMock.getItem("loop.settings.profileName")).toBe("Charles");
  });

  it("displays region as read-only", () => {
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    expect(screen.getByTestId("settings-region-display")).toHaveTextContent("eu-west");
    // No input for region
    expect(screen.queryByRole("textbox", { name: /region/i })).toBeNull();
  });

  it("renders all three theme buttons", () => {
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    expect(screen.getByTestId("settings-theme-light")).toBeInTheDocument();
    expect(screen.getByTestId("settings-theme-dark")).toBeInTheDocument();
    expect(screen.getByTestId("settings-theme-system")).toBeInTheDocument();
  });

  it("marks active theme with aria-pressed=true", () => {
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    // Default theme is "system"
    expect(screen.getByTestId("settings-theme-system")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("settings-theme-light")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("persists theme selection to localStorage", () => {
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByTestId("settings-theme-dark"));
    expect(localStorageMock.getItem("loop.settings.theme")).toBe("dark");
  });

  it("calls onClose when backdrop is clicked", () => {
    const onClose = vi.fn();
    render(<SettingsDrawer open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("settings-backdrop"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(<SettingsDrawer open={true} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("settings-close"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("reads persisted theme from localStorage on mount", () => {
    localStorageMock.setItem("loop.settings.theme", "dark");
    render(<SettingsDrawer open={true} onClose={() => {}} />);
    expect(screen.getByTestId("settings-theme-dark")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("reads persisted profileName from localStorage on mount", () => {
    localStorageMock.setItem("loop.settings.profileName", "Stored Name");
    render(<SettingsDrawer open={true} onClose={() => {}} defaultProfileName="Default" />);
    const input = screen.getByTestId("settings-profile-name-input") as HTMLInputElement;
    expect(input.value).toBe("Stored Name");
  });
});

describe("SettingsButton", () => {
  it("calls onClick when clicked", () => {
    const onClick = vi.fn();
    render(<SettingsButton onClick={onClick} />);
    fireEvent.click(screen.getByTestId("settings-open-button"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});

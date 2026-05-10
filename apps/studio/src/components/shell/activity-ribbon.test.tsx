import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: vi.fn(),
}));

import { ActivityRibbon } from "@/components/shell/activity-ribbon";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

const mockedUseActiveWorkspace = vi.mocked(useActiveWorkspace);

describe("ActivityRibbon", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("renders activity intensity from the workspace activity backend", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: { id: "ws_acme", name: "Acme", slug: "acme", role: "owner" },
      isLoading: false,
      setActive: vi.fn(),
    });
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        turn_rate_per_minute: 42,
        ribbon_intensity: 0.6,
        tone: "live",
      }),
    );
    vi.stubGlobal("fetch", fetcher);

    render(<ActivityRibbon />);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-activity-ribbon")).toHaveAttribute(
        "title",
        "42 turns/min",
      );
    });
    expect(screen.getByTestId("workspace-activity-ribbon-fill")).toHaveStyle({
      width: "60%",
      opacity: "0.6",
    });
  });

  it("does not show a colored live ribbon when activity data is unavailable", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: { id: "ws_acme", name: "Acme", slug: "acme", role: "owner" },
      isLoading: false,
      setActive: vi.fn(),
    });

    render(<ActivityRibbon />);

    await waitFor(() => {
      expect(screen.getByTestId("workspace-activity-ribbon")).toHaveAttribute(
        "title",
        "Activity unavailable",
      );
    });
    expect(screen.getByTestId("workspace-activity-ribbon-fill")).toHaveStyle({
      width: "0%",
      opacity: "0",
    });
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: vi.fn(),
}));

import { TelemetryConsentCard } from "@/components/help/telemetry-consent-card";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

const mockedUseActiveWorkspace = vi.mocked(useActiveWorkspace);

describe("TelemetryConsentCard", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("shows backend-required errors instead of treating consent as saved locally", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: { id: "ws_acme", name: "Acme", slug: "acme", role: "owner" },
      isLoading: false,
      setActive: vi.fn(),
    });

    render(<TelemetryConsentCard />);

    expect(await screen.findByTestId("telemetry-consent-card")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("telemetry-consent-card")).toBeInTheDocument();
  });
});

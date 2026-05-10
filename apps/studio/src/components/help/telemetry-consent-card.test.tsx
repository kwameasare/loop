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

  it("shows and enforces workspace admin overrides", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    mockedUseActiveWorkspace.mockReturnValue({
      workspaces: [],
      active: { id: "ws_acme", name: "Acme", slug: "acme", role: "owner" },
      isLoading: false,
      setActive: vi.fn(),
    });
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      if (url === "https://cp.test/v1/workspaces/ws_acme/telemetry-consent") {
        if (init?.method === "POST") {
          expect(JSON.parse(String(init.body))).toMatchObject({
            ai_improvement: false,
          });
          return Response.json({
            workspace_id: "ws_acme",
            user_sub: "builder",
            product_analytics: true,
            diagnostics: true,
            ai_improvement: false,
            crash_reports: true,
            annual_review_due: false,
            admin_overrides: { ai_improvement: false },
          });
        }
        return Response.json({
          workspace_id: "ws_acme",
          user_sub: "builder",
          product_analytics: true,
          diagnostics: true,
          ai_improvement: true,
          crash_reports: true,
          annual_review_due: true,
          admin_overrides: { ai_improvement: false },
        });
      }
      return Response.json({}, { status: 404 });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<TelemetryConsentCard />);

    const aiToggle = await screen.findByTestId(
      "telemetry-toggle-ai_improvement",
    );
    expect(aiToggle).toHaveTextContent("Locked off");
    expect(aiToggle).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws_acme/telemetry-consent",
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});

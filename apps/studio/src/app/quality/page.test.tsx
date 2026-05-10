import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_QUALITY_REPORTS } from "@/lib/quality";

import QualityPage from "./page";

const qualityMocks = vi.hoisted(() => ({
  fetchQualityReports: vi.fn(),
  saveQualityReport: vi.fn(),
}));

const workspaceMocks = vi.hoisted(() => ({
  useActiveWorkspace: vi.fn(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: workspaceMocks.useActiveWorkspace,
}));

vi.mock("@/lib/quality", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/quality")>("@/lib/quality");
  return {
    ...actual,
    fetchQualityReports: qualityMocks.fetchQualityReports,
    saveQualityReport: qualityMocks.saveQualityReport,
  };
});

describe("QualityPage", () => {
  beforeEach(() => {
    qualityMocks.fetchQualityReports.mockReset();
    qualityMocks.saveQualityReport.mockReset();
    workspaceMocks.useActiveWorkspace.mockReturnValue({
      active: { id: "ws_quality", name: "Quality Workspace" },
      isLoading: false,
    });
  });

  it("shows a degraded state when control-plane reports cannot load", async () => {
    qualityMocks.fetchQualityReports.mockRejectedValue(
      new Error("cp-api GET quality reports -> 503"),
    );

    render(<QualityPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Quality reports are unavailable/i);
      expect(state).toHaveTextContent(/cannot claim screen readiness/i);
      expect(state).toHaveTextContent(/cp-api GET quality reports/i);
    });
  });

  it("keeps the dashboard empty instead of substituting sample reports", async () => {
    qualityMocks.fetchQualityReports.mockResolvedValue([]);

    render(<QualityPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/No quality reports have been recorded/i),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("quality-summary")).toHaveTextContent(
      "Screens reviewed0",
    );
    expect(screen.queryByText("/agents/[id]/workbench")).toBeNull();
  });

  it("opens a live report checklist and persists edits", async () => {
    const report = SAMPLE_QUALITY_REPORTS[0]!;
    qualityMocks.fetchQualityReports.mockResolvedValue([report]);
    qualityMocks.saveQualityReport.mockImplementation(
      (_workspaceId: string, nextReport: typeof report) =>
        Promise.resolve(nextReport),
    );

    render(<QualityPage />);

    fireEvent.click(
      await screen.findByTestId("quality-row-/agents/[id]/workbench"),
    );
    fireEvent.click(screen.getByLabelText(/One primary job is named/i));

    await waitFor(() => {
      expect(qualityMocks.saveQualityReport).toHaveBeenCalledWith(
        "ws_quality",
        expect.objectContaining({
          screen: "/agents/[id]/workbench",
        }),
      );
    });
  });
});

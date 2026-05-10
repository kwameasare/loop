import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OnboardingPage from "./page";

const onboardingMocks = vi.hoisted(() => ({
  fetchWeeklyRecap: vi.fn(),
  runConciergeFromWorkspace: vi.fn(),
}));

const workspaceMocks = vi.hoisted(() => ({
  useActiveWorkspace: vi.fn(),
}));

const userMocks = vi.hoisted(() => ({
  useUser: vi.fn(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: workspaceMocks.useActiveWorkspace,
}));

vi.mock("@/lib/use-user", () => ({
  useUser: userMocks.useUser,
}));

vi.mock("@/lib/onboarding", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/onboarding")>(
      "@/lib/onboarding",
    );
  return {
    ...actual,
    fetchWeeklyRecap: onboardingMocks.fetchWeeklyRecap,
    runConciergeFromWorkspace: onboardingMocks.runConciergeFromWorkspace,
  };
});

describe("OnboardingPage", () => {
  beforeEach(() => {
    onboardingMocks.fetchWeeklyRecap.mockReset();
    onboardingMocks.runConciergeFromWorkspace.mockReset();
    workspaceMocks.useActiveWorkspace.mockReturnValue({
      active: { id: "ws_onboarding", name: "Onboarding Workspace" },
      isLoading: false,
    });
    userMocks.useUser.mockReturnValue({
      user: { sub: "builder-1", email: "builder@acme.test" },
      isAuthenticated: true,
      isLoading: false,
    });
  });

  it("loads the first-month recap from workspace activity", async () => {
    onboardingMocks.fetchWeeklyRecap.mockResolvedValue({
      weekOf: "2026-05-04",
      promotions: 1,
      rollbacks: 0,
      evalsSaved: 2,
      kbSourcesUpdated: 1,
      costDeltaPercent: 0,
      latencyDeltaPercent: -3,
    });

    render(<OnboardingPage />);

    expect(await screen.findByTestId("onboarding-recap")).toHaveTextContent(
      "This week: 1 promotions, 0 rollbacks, 2 evals saved, 1 KB sources updated. Cost unchanged, latency -3%.",
    );
    expect(screen.queryByText(/4 promotions, 2 rollbacks/i)).toBeNull();
  });

  it("shows degraded recap evidence instead of sample progress", async () => {
    onboardingMocks.fetchWeeklyRecap.mockRejectedValue(
      new Error("cp-api GET onboarding recap -> 503"),
    );

    render(<OnboardingPage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Onboarding recap/i);
      expect(state).toHaveTextContent(
        /control plane returns real workspace activity/i,
      );
      expect(state).toHaveTextContent(/cp-api GET onboarding recap/i);
    });
    expect(screen.queryByText(/4 promotions, 2 rollbacks/i)).toBeNull();
  });

  it("runs concierge analysis through the active workspace with the signed-in reviewer", async () => {
    onboardingMocks.fetchWeeklyRecap.mockResolvedValue({
      weekOf: "2026-05-04",
      promotions: 0,
      rollbacks: 0,
      evalsSaved: 0,
      kbSourcesUpdated: 0,
      costDeltaPercent: 0,
      latencyDeltaPercent: 0,
    });
    onboardingMocks.runConciergeFromWorkspace.mockResolvedValue({
      consent: {
        acceptedAt: "2026-05-10T10:00:00Z",
        conversationsRequested: 20,
        scopes: ["transcripts"],
        reviewer: "builder@acme.test",
      },
      recommendations: {
        starterEvalIds: ["eval_from_trace_123"],
        kbHoles: [],
        scenes: ["scene_123"],
        riskyTools: [],
        safeFirstImprovement:
          "Save the highest-risk recent conversation as an eval.",
      },
    });

    render(<OnboardingPage />);

    fireEvent.click(await screen.findByTestId("concierge-accept"));

    await waitFor(() => {
      expect(onboardingMocks.runConciergeFromWorkspace).toHaveBeenCalledWith(
        "ws_onboarding",
        expect.objectContaining({
          conversationsRequested: 20,
          reviewer: "builder@acme.test",
          scopes: ["transcripts"],
        }),
      );
    });
    expect(await screen.findByTestId("concierge-result")).toHaveTextContent(
      "eval_from_trace_123",
    );
  });
});

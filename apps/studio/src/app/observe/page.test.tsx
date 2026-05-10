import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ObservePage from "./page";

const observatoryMocks = vi.hoisted(() => ({
  fetchObservatoryModel: vi.fn(),
}));

vi.mock("@/components/auth/require-auth", () => ({
  RequireAuth: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("@/lib/use-active-workspace", () => ({
  useActiveWorkspace: () => ({
    active: { id: "ws_observe", name: "Observe Workspace" },
    isLoading: false,
  }),
}));

vi.mock("@/lib/observatory", () => ({
  fetchObservatoryModel: observatoryMocks.fetchObservatoryModel,
}));

describe("ObservePage", () => {
  beforeEach(() => {
    observatoryMocks.fetchObservatoryModel.mockReset();
  });

  it("shows degraded observability evidence instead of a raw route alert", async () => {
    observatoryMocks.fetchObservatoryModel.mockRejectedValue(
      new Error("cp-api GET observatory telemetry -> 503"),
    );

    render(<ObservePage />);

    await waitFor(() => {
      const state = screen.getByTestId("target-state");
      expect(state).toHaveAttribute("data-state", "degraded");
      expect(state).toHaveTextContent(/Observatory is degraded/i);
      expect(state).toHaveTextContent(/telemetry, incidents, and anomaly/i);
      expect(state).toHaveTextContent(/cp-api GET observatory telemetry/i);
    });
  });
});

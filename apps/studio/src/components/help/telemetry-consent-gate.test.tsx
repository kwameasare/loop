import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/help/telemetry-consent-card", () => ({
  TelemetryConsentCard: () => <section data-testid="telemetry-consent-card" />,
}));

import { TelemetryConsentGate } from "@/components/help/telemetry-consent-gate";

describe("TelemetryConsentGate", () => {
  it("mounts consent in a route-agnostic shell overlay", () => {
    render(<TelemetryConsentGate />);

    expect(screen.getByTestId("telemetry-consent-gate")).toHaveClass(
      "fixed",
    );
    expect(screen.getByTestId("telemetry-consent-card")).toBeInTheDocument();
  });
});

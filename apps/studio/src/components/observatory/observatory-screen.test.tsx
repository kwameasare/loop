import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import { OBSERVATORY_MODEL } from "@/lib/observatory";

describe("ObservatoryScreen", () => {
  it("renders dashboards, anomalies, production tail, and ambient health", () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    expect(screen.getByTestId("observatory-dashboards")).toHaveTextContent(
      "Quality",
    );
    expect(screen.getByTestId("observatory-anomalies")).toHaveTextContent(
      "Anomaly cards",
    );
    expect(screen.getByText("Production tail")).toBeInTheDocument();
    expect(screen.getByTestId("ambient-health-arcs")).toHaveTextContent(
      "Ambient agent health",
    );
  });

  it("allows operators to pause the production tail", () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByRole("button", { name: /pause tail/i }));

    expect(screen.getByText("paused")).toBeInTheDocument();
  });
});

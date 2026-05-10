import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByTestId("observatory-incidents")).toHaveTextContent(
      "Incident response",
    );
    expect(screen.getByTestId("observatory-incidents")).toHaveTextContent(
      "error_rate breached",
    );
    expect(
      screen.getByTestId("incident-notifications-inc_rollback_schema"),
    ).toHaveTextContent("maya@acme.test");
    expect(screen.getByTestId("ambient-health-arcs")).toHaveTextContent(
      "Ambient agent health",
    );
  });

  it("allows operators to pause the production tail", () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByRole("button", { name: /pause tail/i }));

    expect(screen.getByText("paused")).toBeInTheDocument();
  });

  it("seeds incident evals from the incident panel", async () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByTestId("incident-seed-inc_rollback_schema"));

    expect(
      await screen.findByTestId("incident-suite-inc_rollback_schema"),
    ).toHaveTextContent("suite_incident_regressions_local");
  });

  it("creates a fix Change Package from an incident", async () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(
      screen.getByTestId("incident-fix-package-inc_rollback_schema"),
    );

    expect(
      await screen.findByTestId("incident-fix-package-id-inc_rollback_schema"),
    ).toHaveTextContent("cp_inc_rollback_schema");
  });

  it("moves incidents through investigate, resolve, and archive actions", async () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(
      screen.getByTestId("incident-investigate-inc_rollback_schema"),
    );
    await waitFor(() => {
      expect(
        screen.getByTestId("incident-card-inc_rollback_schema"),
      ).toHaveTextContent("investigating");
    });

    fireEvent.click(screen.getByTestId("incident-resolve-inc_rollback_schema"));
    await waitFor(() => {
      expect(
        screen.getByTestId("incident-card-inc_rollback_schema"),
      ).toHaveTextContent("resolved");
    });

    fireEvent.click(screen.getByTestId("incident-archive-inc_rollback_schema"));
    await waitFor(() => {
      expect(
        screen.getByTestId("incident-card-inc_rollback_schema"),
      ).toHaveTextContent("archived");
    });
  });
});

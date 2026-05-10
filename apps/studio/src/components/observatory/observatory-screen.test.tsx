import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import { OBSERVATORY_MODEL } from "@/lib/observatory";

describe("ObservatoryScreen", () => {
  const ORIGINAL_BASE_URL = process.env.LOOP_CP_API_BASE_URL;

  function mockIncidentBackend() {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const incident = OBSERVATORY_MODEL.incidents[0]!;
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.endsWith("/eval-cases")) {
        return Response.json({
          ok: true,
          suite_id: "suite_incident_regressions_live",
          case_ids: ["case_incident_1"],
          incident: {
            ...incident,
            candidate_eval_suite_id: "suite_incident_regressions_live",
          },
        });
      }
      if (url.endsWith("/change-package")) {
        return Response.json({
          ok: true,
          change_package: { id: "cp_incident_live" },
          incident: {
            ...incident,
            status: "fix_staged",
            fix_change_package_id: "cp_incident_live",
          },
        });
      }
      const action = url.split("/").pop();
      const status =
        action === "archive"
          ? "archived"
          : action === "resolve"
            ? "resolved"
            : action === "investigate"
              ? "investigating"
              : incident.status;
      return Response.json({ ...incident, status });
    });
    vi.stubGlobal("fetch", fetcher);
    return fetcher;
  }

  afterEach(() => {
    if (ORIGINAL_BASE_URL === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = ORIGINAL_BASE_URL;
    }
    vi.unstubAllGlobals();
  });

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
    mockIncidentBackend();
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByTestId("incident-seed-inc_rollback_schema"));

    expect(
      await screen.findByTestId("incident-suite-inc_rollback_schema"),
    ).toHaveTextContent("suite_incident_regressions_live");
  });

  it("creates a fix Change Package from an incident", async () => {
    mockIncidentBackend();
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(
      screen.getByTestId("incident-fix-package-inc_rollback_schema"),
    );

    expect(
      await screen.findByTestId("incident-fix-package-id-inc_rollback_schema"),
    ).toHaveTextContent("cp_incident_live");
  });

  it("moves incidents through investigate, resolve, and archive actions", async () => {
    mockIncidentBackend();
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

  it("shows backend-required errors instead of local incident mutations", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByTestId("incident-seed-inc_rollback_schema"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("incident-suite-inc_rollback_schema"),
    ).not.toBeInTheDocument();
  });
});

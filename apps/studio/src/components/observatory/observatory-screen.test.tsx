import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ObservatoryScreen } from "@/components/observatory/observatory-screen";
import { OBSERVATORY_MODEL } from "@/components/observatory/observatory-test-fixtures";
import { buildObservatoryModel } from "@/lib/observatory";

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
    expect(screen.getByText("Next best operating action")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Patch the escalation classifier, then replay the affected scene.",
      ).length,
    ).toBeGreaterThan(0);
    expect(
      screen.queryByText(/Fix the legal synonym cluster before raising canary/i),
    ).not.toBeInTheDocument();
  });

  it("links anomalies to trace evidence and the relevant agent edit surface", () => {
    render(
      <ObservatoryScreen
        model={OBSERVATORY_MODEL}
        agentId="agent_support"
        workspaceId="ws1"
      />,
    );

    expect(
      screen.getByTestId("anomaly-open-traces-anom_legal_synonym"),
    ).toHaveAttribute(
      "href",
      "/traces?agent_id=agent_support&filter=trace_legal_synonym+OR+scene%3Alegal-threat",
    );
    expect(
      screen.getByTestId("anomaly-open-edit-anom_legal_synonym"),
    ).toHaveAttribute("href", "/agents/agent_support/behavior");
    expect(screen.getByTestId("tail-open-trace-tail_1")).toHaveAttribute(
      "href",
      "/traces/trace_refund_742",
    );
  });

  it("focuses an incident opened from an evidence link", () => {
    render(
      <ObservatoryScreen
        model={OBSERVATORY_MODEL}
        focusedIncidentId="inc_rollback_schema"
      />,
    );

    expect(
      screen.getByTestId("incident-card-inc_rollback_schema"),
    ).toHaveAttribute("data-focused", "true");
    expect(
      screen.getByTestId("incident-focused-inc_rollback_schema"),
    ).toHaveTextContent("incident inc_rollback_schema is focused");
  });

  it("allows operators to pause the production tail", () => {
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} />);

    fireEvent.click(screen.getByRole("button", { name: /pause tail/i }));

    expect(screen.getByText("paused")).toBeInTheDocument();
  });

  it("pins dashboard metrics only after backend persistence succeeds", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toBe(
        "https://cp.test/v1/workspaces/ws1/dashboards",
      );
      expect(init?.method).toBe("POST");
      return Response.json({
        id: "dash_quality",
        name: "Quality watch",
        layout: [
          {
            source_type: "observatory_metric",
            source_id: "quality",
            title: "Quality",
          },
        ],
        shared_with: [],
      });
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ObservatoryScreen model={OBSERVATORY_MODEL} workspaceId="ws1" />);

    fireEvent.click(screen.getByTestId("observatory-pin-quality"));

    expect(await screen.findByText("Pinned")).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("turns production anomalies into tasks and eval cases", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async (input, init) => {
      const url = String(input);
      expect(init?.method).toBe("POST");
      if (url.endsWith("/tasks")) {
        return Response.json({
          id: "task_anom_tool_wait",
          evidence: "task created",
        });
      }
      if (url.endsWith("/eval-cases")) {
        return Response.json({
          id: "eval_anom_tool_wait",
          evidence: "eval created",
        });
      }
      return Response.json({});
    });
    vi.stubGlobal("fetch", fetcher);

    render(<ObservatoryScreen model={OBSERVATORY_MODEL} workspaceId="ws1" />);

    fireEvent.click(screen.getByTestId("anomaly-task-anom_tool_wait"));
    expect(
      await screen.findByTestId("anomaly-action-refs-anom_tool_wait"),
    ).toHaveTextContent("task_anom_tool_wait");

    fireEvent.click(screen.getByTestId("anomaly-eval-anom_tool_wait"));
    expect(
      await screen.findByTestId("anomaly-action-refs-anom_tool_wait"),
    ).toHaveTextContent("eval_anom_tool_wait");

    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws1/observatory/anomalies/anom_tool_wait/tasks",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/workspaces/ws1/observatory/anomalies/anom_tool_wait/eval-cases",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows backend-required errors instead of locally pinning dashboards", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(<ObservatoryScreen model={OBSERVATORY_MODEL} workspaceId="ws1" />);

    fireEvent.click(screen.getByTestId("observatory-pin-quality"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("observatory-pin-quality")).toHaveTextContent(
      "Pin chart to dashboard",
    );
  });

  it("renders unconfigured telemetry as degraded, not healthy fixture posture", () => {
    const model = buildObservatoryModel({
      workspaceId: "ws1",
      traces: [],
      usage: [],
      inbox: [],
      incidents: [],
      nowMs: Date.UTC(2026, 4, 7),
      degradedReason:
        "LOOP_CP_API_BASE_URL is required for live Observatory telemetry.",
    });

    render(<ObservatoryScreen model={model} workspaceId="ws1" />);

    expect(screen.getByTestId("observatory-degraded")).toHaveTextContent(
      /live observatory telemetry is unavailable/i,
    );
    expect(screen.getByTestId("observatory-metric-quality")).toHaveTextContent(
      "Telemetry backend not connected",
    );
    expect(
      screen.getByText(/No production tail events loaded/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/legal synonym cluster/i),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/No operating recommendation is ranked/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No agent health arcs loaded/i),
    ).toBeInTheDocument();
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

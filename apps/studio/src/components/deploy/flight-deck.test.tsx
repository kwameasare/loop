import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  CanarySlider,
  DeployTimeline,
  EnvironmentStrip,
  FlightDeckScreen,
  PreflightGrid,
  PromotionPanel,
  RollbackPanel,
} from ".";
import { fetchDeployFlightModel } from "@/lib/deploy-flight";

describe("EnvironmentStrip", () => {
  it("renders dev/staging/production/region-eu cards with their approval policies", () => {
    render(<EnvironmentStrip />);
    expect(
      within(screen.getByTestId("environment-policy-dev")).getByText(
        /auto-promote/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("environment-policy-production")).getByText(
        /two-person/i,
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("environment-policy-region-eu")).getByText(
        /compliance/i,
      ),
    ).toBeInTheDocument();
  });

  it("invokes onSelect and toggles the active card on click", () => {
    const onSelect = vi.fn();
    render(<EnvironmentStrip onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("environment-card-staging"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("environment-card-staging")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

describe("PreflightGrid", () => {
  it("renders all six canonical dimensions and labels their severity", () => {
    render(<PreflightGrid />);
    for (const dim of [
      "behavior",
      "tool",
      "knowledge",
      "memory",
      "channel",
      "budget",
    ]) {
      expect(screen.getByTestId(`preflight-${dim}`)).toBeInTheDocument();
      expect(
        screen.getByTestId(`preflight-severity-${dim}`),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId(`preflight-evidence-${dim}`),
      ).toBeInTheDocument();
    }
  });
});

describe("PromotionPanel", () => {
  it("locks the promote button until gates and approvals are complete", () => {
    render(<PromotionPanel />);
    const btn = screen.getByTestId("promotion-promote");
    expect(btn).toBeDisabled();
    // Locked-state surface shows a degraded StatePanel.
    const panels = screen.getAllByTestId("state-panel");
    expect(panels.some((p) => p.getAttribute("data-state") === "degraded")).toBe(
      true,
    );
  });

  it("enables the promote button when gates pass and approvals are satisfied", () => {
    const onPromote = vi.fn();
    render(
      <PromotionPanel
        gates={[
          {
            id: "regression",
            label: "Regression",
            status: "passed",
            cases: { passed: 1, total: 1 },
            evidenceRef: "ev/1",
            blocking: true,
          },
        ]}
        approvals={[
          {
            id: "lead",
            role: "Lead",
            required: true,
            satisfied: true,
            approver: "lead@acme",
            approvedAt: "2025-02-21T00:00:00Z",
            evidenceRef: "ev/2",
          },
        ]}
        onPromote={onPromote}
      />,
    );
    const btn = screen.getByTestId("promotion-promote");
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onPromote).toHaveBeenCalledTimes(1);
  });

  it("renders a permission boundary when the caller lacks promote rights", () => {
    render(<PromotionPanel canApprove={false} />);
    expect(screen.queryByTestId("promotion-promote")).not.toBeInTheDocument();
    expect(screen.getByTestId("state-panel")).toHaveAttribute(
      "data-state",
      "permission",
    );
  });
});

describe("CanarySlider", () => {
  it("exposes the canonical 1/10/50/100 stages and switches active radio on click", () => {
    const onChange = vi.fn();
    render(<CanarySlider onChange={onChange} />);
    expect(screen.getByTestId("canary-stage-1")).toBeInTheDocument();
    expect(screen.getByTestId("canary-stage-10")).toHaveAttribute(
      "aria-checked",
      "true",
    );
    fireEvent.click(screen.getByTestId("canary-stage-50"));
    expect(onChange).toHaveBeenCalledWith(50);
    expect(screen.getByTestId("canary-stage-50")).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });

  it("shows live metric comparison and surfaces healthier vs regressing direction", () => {
    render(<CanarySlider />);
    const cost = screen.getByTestId("canary-metric-cost_per_turn");
    expect(cost.querySelector("[data-healthier]")).toHaveAttribute(
      "data-healthier",
      "false",
    );
    const errors = screen.getByTestId("canary-metric-error_rate");
    expect(errors.querySelector("[data-healthier]")).toHaveAttribute(
      "data-healthier",
      "true",
    );
  });

  it("renders four armed (not firing) auto-rollback triggers on the happy path", () => {
    render(<CanarySlider />);
    const triggers = screen
      .getAllByTestId(/^auto-rollback-/)
      .filter((el) => el.getAttribute("data-testid") !== "auto-rollback-triggers");
    expect(triggers).toHaveLength(4);
    for (const t of triggers) {
      expect(t).toHaveAttribute("data-firing", "false");
    }
  });

  it("advance button moves to the next stage", () => {
    render(<CanarySlider />);
    fireEvent.click(screen.getByTestId("canary-advance"));
    expect(screen.getByTestId("canary-stage-50")).toHaveAttribute(
      "aria-checked",
      "true",
    );
  });
});

describe("RollbackPanel", () => {
  it("requires a two-step confirm before invoking onConfirm", () => {
    const onConfirm = vi.fn();
    render(<RollbackPanel onConfirm={onConfirm} />);
    expect(screen.queryByTestId("rollback-confirm")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("rollback-arm"));
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("rollback-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("rollback-recorded")).toHaveTextContent(
      /audited/i,
    );
  });

  it("blocks rollback behind a permission boundary when the caller lacks the role", () => {
    render(<RollbackPanel canRollback={false} />);
    expect(screen.queryByTestId("rollback-arm")).not.toBeInTheDocument();
    expect(screen.getByTestId("state-panel")).toHaveAttribute(
      "data-state",
      "permission",
    );
  });
});

describe("DeployTimeline", () => {
  it("renders the canonical 7 steps in order", () => {
    render(<DeployTimeline />);
    const ids = [
      "build",
      "scan",
      "evals",
      "smoke",
      "canary-10",
      "canary-50",
      "prod-100",
    ];
    for (const id of ids) {
      expect(screen.getByTestId(`deploy-timeline-${id}`)).toBeInTheDocument();
    }
  });
});

describe("FlightDeckScreen", () => {
  it("composes the readiness strip and every flight-deck section", () => {
    render(<FlightDeckScreen />);
    expect(screen.getByTestId("flight-deck-screen")).toBeInTheDocument();
    expect(screen.getByTestId("environment-strip")).toBeInTheDocument();
    expect(screen.getByTestId("preflight-grid")).toBeInTheDocument();
    expect(screen.getByTestId("promotion-panel")).toBeInTheDocument();
    expect(screen.getByTestId("canary-slider")).toBeInTheDocument();
    expect(screen.getByTestId("rollback-panel")).toBeInTheDocument();
    expect(screen.getByTestId("deploy-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("flight-readiness-rollback")).toBeInTheDocument();
  });
});

describe("fetchDeployFlightModel", () => {
  it("derives preflight gates from live trace and audit posture", async () => {
    const fetcher = vi.fn<typeof fetch>(async (input) => {
      const url = String(input);
      if (url.includes("/workspaces/ws-1/traces")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                workspace_id: "ws-1",
                trace_id: "d".repeat(32),
                turn_id: "11111111-1111-4111-8111-111111111111",
                conversation_id: "22222222-2222-4222-8222-222222222222",
                agent_id: "33333333-3333-4333-8333-333333333333",
                started_at: "2026-05-07T12:00:00Z",
                duration_ms: 500,
                span_count: 4,
                error: true,
              },
            ],
            next_cursor: null,
          }),
          { status: 200, headers: { "content-type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          items: [
            {
              id: "ev-1",
              occurred_at: "2026-05-07T12:00:00Z",
              workspace_id: "ws-1",
              actor_sub: "sam@example.com",
              action: "agent.version.promoted",
              resource_type: "agent_version",
              resource_id: "v1",
              outcome: "success",
            },
          ],
          total: 1,
        }),
        { status: 200, headers: { "content-type": "application/json" } },
      );
    });

    const model = await fetchDeployFlightModel("ws-1", {
      baseUrl: "https://cp.example.test/v1",
      fetcher,
    });

    expect(model.diffs[0].severity).toBe("blocking");
    expect(model.gates[0]).toMatchObject({
      id: "live-trace-health",
      status: "failed",
    });
    expect(model.rollbackTarget.versionId).toBe("d".repeat(12));
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CostCapacityPanel } from "./cost-capacity-panel";
import { buildCostCapacityModel, type UsageRecord } from "@/lib/costs";
import { buildLatencyBudgetModel } from "@/lib/latency";

const WS = "ws_test";
const APRIL_1 = Date.UTC(2026, 3, 1);

const records: UsageRecord[] = [
  {
    workspace_id: WS,
    agent_id: "agt_support",
    agent_name: "Support",
    channel: "web",
    model: "gpt-4o",
    environment: "production",
    customer_segment: "enterprise",
    metric: "tokens.in",
    quantity: 1000,
    turn_count: 25,
    day_ms: APRIL_1,
  },
  {
    workspace_id: WS,
    agent_id: "agt_support",
    agent_name: "Support",
    tool_name: "lookup_order",
    metric: "tool_calls",
    quantity: 2,
    day_ms: APRIL_1,
  },
  {
    workspace_id: WS,
    agent_id: "agt_support",
    agent_name: "Support",
    retrieval_source: "refund_policy",
    metric: "retrievals",
    quantity: 6,
    day_ms: APRIL_1,
  },
];

function renderPanel(targetMs = 800) {
  render(
    <CostCapacityPanel
      model={buildCostCapacityModel(records, {
        workspace_id: WS,
        now_ms: Date.UTC(2026, 3, 15),
      })}
      latency={buildLatencyBudgetModel(targetMs)}
    />,
  );
}

describe("CostCapacityPanel", () => {
  it("renders cost surfaces, line-item math, decisions, and latency budget", () => {
    renderPanel();

    expect(screen.getByTestId("cost-capacity-panel")).toBeInTheDocument();
    expect(screen.getByTestId("cost-surface-per_turn")).toHaveTextContent(
      "Per turn",
    );
    expect(screen.getByTestId("cost-surface-per_tool")).toHaveTextContent(
      "lookup_order",
    );
    expect(screen.getByTestId("cost-line-item-math")).toHaveTextContent(
      "Model input",
    );
    expect(screen.getByTestId("cost-decision-degrade_rule")).toHaveTextContent(
      "Quality impact must clear eval gate",
    );
    expect(screen.getByTestId("latency-budget-visualizer")).toHaveTextContent(
      "Latency budget visualizer",
    );
    expect(
      screen.getByTestId("latency-suggestion-cache_pricing_policy"),
    ).toHaveTextContent("retrieval.final_sale_refund");
  });

  it("updates the target marker copy when the slider changes", () => {
    renderPanel();

    fireEvent.change(screen.getByLabelText("Latency target marker"), {
      target: { value: "1200" },
    });

    expect(screen.getByTestId("latency-budget-visualizer")).toHaveTextContent(
      "target marker is 1,200 ms",
    );
    expect(screen.getByTestId("latency-budget-visualizer")).toHaveTextContent(
      "Budget met",
    );
  });

  it("shows unsupported cost dimensions when metadata is absent", () => {
    render(
      <CostCapacityPanel
        model={buildCostCapacityModel([], {
          workspace_id: WS,
          now_ms: Date.UTC(2026, 3, 15),
        })}
        latency={buildLatencyBudgetModel(800)}
      />,
    );

    expect(screen.getByTestId("cost-surface-per_channel")).toHaveTextContent(
      "Unsupported",
    );
    expect(screen.getByTestId("cost-line-runtime")).toHaveTextContent(
      "Unsupported",
    );
  });
});

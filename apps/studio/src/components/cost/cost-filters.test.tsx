/**
 * S285: Tests for cost filters — CostFilterBar, filterRecords, useCostFilters.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import { CostFilterBar } from "./cost-filter-bar";
import {
  EMPTY_FILTERS,
  filterRecords,
  type CostFilters,
  type UsageRecord,
} from "@/lib/costs";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const WS = "ws_x";
const DAY1 = Date.UTC(2026, 3, 1);
const DAY2 = Date.UTC(2026, 3, 5);
const DAY3 = Date.UTC(2026, 3, 10);

const RECORDS: UsageRecord[] = [
  {
    workspace_id: WS,
    agent_id: "agt_support",
    agent_name: "Support",
    channel: "web",
    model: "gpt-4o",
    metric: "tokens.in",
    quantity: 1000,
    day_ms: DAY1,
  },
  {
    workspace_id: WS,
    agent_id: "agt_support",
    agent_name: "Support",
    channel: "whatsapp",
    model: "gpt-4o-mini",
    metric: "tokens.out",
    quantity: 500,
    day_ms: DAY2,
  },
  {
    workspace_id: WS,
    agent_id: "agt_sales",
    agent_name: "Sales",
    channel: "web",
    model: "gpt-4o",
    metric: "tool_calls",
    quantity: 20,
    day_ms: DAY3,
  },
];

const AGENTS = [
  { id: "agt_support", name: "Support" },
  { id: "agt_sales", name: "Sales" },
];
const CHANNELS = ["web", "whatsapp"];
const MODELS = ["gpt-4o", "gpt-4o-mini"];

// ---------------------------------------------------------------------------
// filterRecords unit tests
// ---------------------------------------------------------------------------

describe("filterRecords", () => {
  it("returns all records when filters are empty", () => {
    expect(filterRecords(RECORDS, EMPTY_FILTERS)).toHaveLength(3);
  });

  it("filters by agent_id", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      agent_id: "agt_sales",
    });
    expect(result).toHaveLength(1);
    expect(result[0].agent_id).toBe("agt_sales");
  });

  it("filters by channel", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      channel: "whatsapp",
    });
    expect(result).toHaveLength(1);
    expect(result[0].channel).toBe("whatsapp");
  });

  it("filters by model", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      model: "gpt-4o-mini",
    });
    expect(result).toHaveLength(1);
    expect(result[0].model).toBe("gpt-4o-mini");
  });

  it("filters by date_from (ms string)", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      date_from: String(DAY2),
    });
    expect(result).toHaveLength(2);
    expect(result.every((r) => r.day_ms >= DAY2)).toBe(true);
  });

  it("filters by date_to (ms string)", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      date_to: String(DAY1),
    });
    expect(result).toHaveLength(1);
    expect(result[0].day_ms).toBe(DAY1);
  });

  it("combines multiple filters", () => {
    const result = filterRecords(RECORDS, {
      ...EMPTY_FILTERS,
      agent_id: "agt_support",
      channel: "web",
    });
    expect(result).toHaveLength(1);
    expect(result[0].model).toBe("gpt-4o");
  });
});

// ---------------------------------------------------------------------------
// CostFilterBar component tests
// ---------------------------------------------------------------------------

describe("CostFilterBar", () => {
  it("renders all four filter controls", () => {
    render(
      <CostFilterBar
        filters={EMPTY_FILTERS}
        agents={AGENTS}
        channels={CHANNELS}
        models={MODELS}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.getByTestId("filter-agent")).toBeInTheDocument();
    expect(screen.getByTestId("filter-channel")).toBeInTheDocument();
    expect(screen.getByTestId("filter-model")).toBeInTheDocument();
    expect(screen.getByTestId("filter-date-from")).toBeInTheDocument();
    expect(screen.getByTestId("filter-date-to")).toBeInTheDocument();
  });

  it("does not show reset button when all filters are empty", () => {
    render(
      <CostFilterBar
        filters={EMPTY_FILTERS}
        agents={AGENTS}
        channels={CHANNELS}
        models={MODELS}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("filter-reset")).toBeNull();
  });

  it("shows reset button when any filter is active", () => {
    render(
      <CostFilterBar
        filters={{ ...EMPTY_FILTERS, agent_id: "agt_support" }}
        agents={AGENTS}
        channels={CHANNELS}
        models={MODELS}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    );
    expect(screen.getByTestId("filter-reset")).toBeInTheDocument();
  });

  it("calls onChange with updated agent_id when agent filter changes", () => {
    const onChange = vi.fn();
    render(
      <CostFilterBar
        filters={EMPTY_FILTERS}
        agents={AGENTS}
        channels={CHANNELS}
        models={MODELS}
        onChange={onChange}
        onReset={vi.fn()}
      />,
    );
    fireEvent.change(screen.getByTestId("filter-agent"), {
      target: { value: "agt_sales" },
    });
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ agent_id: "agt_sales" }),
    );
  });

  it("calls onReset when reset button is clicked", () => {
    const onReset = vi.fn();
    render(
      <CostFilterBar
        filters={{ ...EMPTY_FILTERS, channel: "web" }}
        agents={AGENTS}
        channels={CHANNELS}
        models={MODELS}
        onChange={vi.fn()}
        onReset={onReset}
      />,
    );
    fireEvent.click(screen.getByTestId("filter-reset"));
    expect(onReset).toHaveBeenCalledTimes(1);
  });
});

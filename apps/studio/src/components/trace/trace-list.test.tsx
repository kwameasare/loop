import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { TraceList } from "./trace-list";
import type { TraceSummary } from "@/lib/traces";

function rows(): TraceSummary[] {
  return [
    {
      id: "trc_001",
      agent_id: "agt_a",
      agent_name: "Alpha",
      root_name: "POST /v1/agents/{id}/turns",
      status: "ok",
      duration_ns: 100_000_000,
      started_at_ms: 1_700_000_000_000,
      span_count: 4,
    },
    {
      id: "trc_002",
      agent_id: "agt_b",
      agent_name: "Beta",
      root_name: "POST /v1/agents/{id}/messages",
      status: "error",
      duration_ns: 200_000_000,
      started_at_ms: 1_700_000_060_000,
      span_count: 6,
    },
    {
      id: "trc_003",
      agent_id: "agt_a",
      agent_name: "Alpha",
      root_name: "POST /v1/agents/{id}/runs",
      status: "ok",
      duration_ns: 300_000_000,
      started_at_ms: 1_700_000_120_000,
      span_count: 2,
    },
  ];
}

describe("TraceList", () => {
  it("renders a row per trace with a link to the detail page", () => {
    render(<TraceList traces={rows()} />);
    expect(screen.getByTestId("trace-row-trc_001")).toBeInTheDocument();
    expect(screen.getByTestId("trace-link-trc_002")).toHaveAttribute(
      "href",
      "/traces/trc_002",
    );
    expect(screen.getByTestId("trace-count")).toHaveTextContent("3 traces");
  });

  it("filters by status", () => {
    render(<TraceList traces={rows()} />);
    fireEvent.change(screen.getByTestId("trace-filter-status"), {
      target: { value: "error" },
    });
    expect(screen.getByTestId("trace-count")).toHaveTextContent("1 trace");
    expect(screen.getByTestId("trace-row-trc_002")).toBeInTheDocument();
    expect(screen.queryByTestId("trace-row-trc_001")).toBeNull();
  });

  it("supports free-text search across endpoint", () => {
    render(<TraceList traces={rows()} />);
    fireEvent.change(screen.getByTestId("trace-search"), {
      target: { value: "messages" },
    });
    expect(screen.getByTestId("trace-row-trc_002")).toBeInTheDocument();
    expect(screen.queryByTestId("trace-row-trc_001")).toBeNull();
  });

  it("paginates and disables prev on first page", () => {
    const many: TraceSummary[] = Array.from({ length: 15 }, (_, i) => ({
      ...rows()[0],
      id: `trc_p${i}`,
      started_at_ms: 1_700_000_000_000 + i * 1000,
    }));
    render(<TraceList traces={many} initialPageSize={10} />);
    expect(screen.getByTestId("trace-page-indicator")).toHaveTextContent(
      "Page 1 of 2",
    );
    expect(screen.getByTestId("trace-prev")).toBeDisabled();
    fireEvent.click(screen.getByTestId("trace-next"));
    expect(screen.getByTestId("trace-page-indicator")).toHaveTextContent(
      "Page 2 of 2",
    );
    expect(screen.getByTestId("trace-next")).toBeDisabled();
  });

  it("shows empty state when no rows match", () => {
    render(<TraceList traces={rows()} />);
    fireEvent.change(screen.getByTestId("trace-search"), {
      target: { value: "zzznomatchzzz" },
    });
    expect(screen.getByTestId("trace-empty")).toBeInTheDocument();
  });
});

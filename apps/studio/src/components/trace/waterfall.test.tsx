import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { TraceWaterfall } from "./waterfall";
import type { Trace } from "@/lib/traces";

const trace: Trace = {
  id: "t",
  spans: [
    {
      id: "root",
      parent_id: null,
      name: "POST /turns",
      kind: "server",
      service: "runtime",
      start_ns: 0,
      end_ns: 1000,
      status: "ok",
      attributes: { "http.method": "POST" },
      events: [],
    },
    {
      id: "child",
      parent_id: "root",
      name: "kb.retrieve",
      kind: "internal",
      service: "kb",
      start_ns: 100,
      end_ns: 400,
      status: "error",
      attributes: { top_k: 5 },
      events: [{ name: "cache_miss", timestamp_ns: 150 }],
    },
  ],
};

describe("TraceWaterfall", () => {
  it("renders one row per span and selects the first by default", () => {
    render(<TraceWaterfall trace={trace} />);
    const rows = screen.getAllByTestId("span-row");
    expect(rows).toHaveLength(2);
    // Default selection -> root span name in detail header.
    expect(screen.getByTestId("span-detail")).toHaveTextContent("POST /turns");
  });

  it("selecting another row updates the detail pane", () => {
    render(<TraceWaterfall trace={trace} />);
    const rows = screen.getAllByTestId("span-row");
    fireEvent.click(rows[1]);
    expect(screen.getByTestId("span-detail")).toHaveTextContent("kb.retrieve");
  });

  it("can switch tabs in the detail pane", () => {
    render(<TraceWaterfall trace={trace} />);
    fireEvent.click(screen.getAllByTestId("span-row")[1]);
    fireEvent.click(screen.getByTestId("span-tab-events"));
    expect(screen.getByTestId("span-panel-events")).toHaveTextContent(
      "cache_miss",
    );
    fireEvent.click(screen.getByTestId("span-tab-raw"));
    expect(screen.getByTestId("span-panel-raw")).toHaveTextContent(
      '"id": "child"',
    );
  });
});

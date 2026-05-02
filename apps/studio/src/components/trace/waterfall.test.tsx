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

import type { Span } from "@/lib/traces";

describe("TraceWaterfall — inline attrs + perf", () => {
  it("expands inline attributes for the selected span", () => {
    render(<TraceWaterfall trace={trace} />);
    fireEvent.click(screen.getAllByTestId("span-row")[1]);
    expect(screen.getByTestId("span-attrs-inline-child")).toHaveTextContent(
      "top_k",
    );
    // Switching selection moves the inline attrs panel.
    fireEvent.click(screen.getAllByTestId("span-row")[0]);
    expect(screen.getByTestId("span-attrs-inline-root")).toBeInTheDocument();
    expect(screen.queryByTestId("span-attrs-inline-child")).toBeNull();
  });

  it("renders 200 spans within the perf budget", () => {
    const spans: Span[] = [
      {
        id: "root",
        parent_id: null,
        name: "root",
        kind: "server",
        service: "runtime",
        start_ns: 0,
        end_ns: 200_000,
        status: "ok",
        attributes: {},
        events: [],
      },
    ];
    for (let i = 1; i < 200; i += 1) {
      spans.push({
        id: `s${i}`,
        parent_id: i === 1 || i % 5 === 0 ? "root" : `s${i - 1}`,
        name: `op_${i}`,
        kind: "internal",
        service: "svc",
        start_ns: i * 1000,
        end_ns: i * 1000 + 800,
        status: "ok",
        attributes: { i },
        events: [],
      });
    }
    const start = performance.now();
    render(<TraceWaterfall trace={{ id: "perf", spans }} />);
    const elapsed = performance.now() - start;
    // Real DOM target is <=10ms; jsdom is ~5-10x slower so we assert
    // a generous ceiling (200ms) that still catches O(n^2) regressions.
    expect(elapsed).toBeLessThan(200);
    expect(screen.getAllByTestId("span-bar")).toHaveLength(200);
    expect(screen.getByTestId("trace-waterfall-svg")).toBeInTheDocument();
  });
});

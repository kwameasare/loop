import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { LatencyBudgetVisualizer } from "@/components/trace/latency-budget";
import type { Trace } from "@/lib/traces";

const trace: Trace = {
  id: "trace_1",
  spans: [
    {
      id: "span_turn",
      parent_id: null,
      name: "runtime turn",
      service: "runtime",
      kind: "server",
      category: "channel",
      start_ns: 0,
      end_ns: 180_000_000,
      status: "ok",
      attributes: {},
      events: [],
    },
  ],
};

describe("LatencyBudgetVisualizer", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  afterEach(() => {
    if (previousBaseUrl === undefined) {
      delete process.env.LOOP_CP_API_BASE_URL;
    } else {
      process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    }
    vi.unstubAllGlobals();
  });

  it("surfaces trace-summary latency without inventing span-level suggestions", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json({
          trace_id: "trace_1",
          target_latency_ms: 900,
          total_latency_ms: 180,
          gap_ms: 0,
          spans: [
            {
              id: "trace_1",
              label: "Recorded turn summary",
              ms: 180,
              kind: "trace",
              evidence_ref: "trace/trace_1/summary",
            },
          ],
          suggestions: [],
          unavailable_reason:
            "Span-level latency breakdown is not mounted for this trace yet.",
        }),
      ),
    );

    render(<LatencyBudgetVisualizer agentId="agent_support" trace={trace} />);

    expect(
      await screen.findByTestId("latency-budget-unavailable"),
    ).toHaveTextContent("Span-level latency breakdown");
    expect(screen.getByTestId("latency-budget-no-suggestions")).toHaveTextContent(
      "No latency optimization suggestions",
    );
    expect(screen.getByTestId("latency-budget-visualizer")).toHaveTextContent(
      "180 ms / 900 ms",
    );
  });
});

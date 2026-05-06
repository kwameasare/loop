import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";

import { TraceTheater } from "./trace-theater";
import type { Trace } from "@/lib/traces";

const trace: Trace = {
  id: "trace_refund_742",
  title: "Customer asks to cancel an annual renewal",
  summary: {
    agent_name: "Acme Support Concierge",
    channel: "web",
    deploy_version: "v23.1.4",
    environment: "dev",
    eval_score: 96,
    eval_suite: "Refund and cancellation parity",
    memory_writes: 1,
    model: "gpt-4.1-mini",
    outcome: "Answered with grounded cancellation steps; no refund issued.",
    provider: "OpenAI",
    retrieval_count: 2,
    snapshot_id: "snap_refund_may",
    tool_count: 1,
    total_cost_usd: 0.043,
    total_latency_ns: 1_030_000_000,
  },
  explanations: [
    {
      confidence: 0,
      confidence_level: "unsupported",
      evidence: "No hidden reasoning span is recorded.",
      id: "unsupported",
      source_span_id: "span_answer",
      statement:
        "Unsupported. The trace does not expose private model reasoning.",
      title: "No evidence for private model reasoning",
    },
  ],
  spans: [
    {
      attributes: {},
      category: "channel",
      end_ns: 1_030_000_000,
      events: [],
      id: "span_turn",
      kind: "server",
      name: "web.turn.accepted",
      parent_id: null,
      service: "runtime",
      start_ns: 0,
      status: "ok",
    },
  ],
};

describe("TraceTheater", () => {
  it("renders the canonical summary and evidence-backed explanation", () => {
    render(<TraceTheater trace={trace} />);
    expect(screen.getByTestId("trace-summary")).toHaveTextContent(
      "Answered with grounded cancellation steps",
    );
    expect(screen.getByTestId("trace-summary")).toHaveTextContent(
      "gpt-4.1-mini",
    );
    expect(screen.getByTestId("trace-summary")).toHaveTextContent("96%");
    expect(screen.getByTestId("trace-explanations")).toHaveTextContent(
      "Unsupported. The trace does not expose private model reasoning.",
    );
    expect(screen.getByText(/Source: span_answer/)).toBeInTheDocument();
  });

  it("shows a degraded state when trace metadata is missing", () => {
    render(<TraceTheater trace={{ id: "partial", spans: trace.spans }} />);
    expect(screen.getByText("Trace metadata unavailable")).toBeInTheDocument();
    expect(screen.getAllByTestId("state-panel")[0]).toHaveTextContent(
      "Trace metadata unavailable",
    );
    expect(screen.getByTestId("trace-waterfall")).toBeInTheDocument();
  });
});

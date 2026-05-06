import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";

import { TraceScrubber } from "./trace-scrubber";
import type { Trace } from "@/lib/traces";

const trace: Trace = {
  id: "trace_refund_742",
  summary: {
    agent_name: "Acme Support Concierge",
    channel: "web",
    deploy_version: "v23.1.4",
    environment: "dev",
    eval_score: 96,
    eval_suite: "Refund and cancellation parity",
    memory_writes: 1,
    model: "gpt-4.1-mini",
    outcome: "Answered",
    provider: "OpenAI",
    retrieval_count: 1,
    snapshot_id: "snap_refund_may",
    tool_count: 1,
    total_cost_usd: 0.04,
    total_latency_ns: 600,
  },
  spans: [
    {
      id: "span_context",
      parent_id: null,
      name: "kb.retrieve.refund_policy",
      category: "retrieval",
      kind: "internal",
      service: "kb",
      start_ns: 0,
      end_ns: 100,
      status: "ok",
      attributes: {},
      events: [],
      input: { query: "refund" },
      normalized_payload: { chunks: [{ id: "refund_policy_2026.pdf#p4" }] },
    },
    {
      id: "span_tool",
      parent_id: null,
      name: "tool.lookup_order",
      category: "tool",
      kind: "client",
      service: "tool",
      start_ns: 110,
      end_ns: 300,
      status: "ok",
      attributes: { tool: "lookup_order" },
      events: [],
    },
  ],
};

describe("TraceScrubber", () => {
  it("scrubs between recorded frames and shows per-frame evidence", () => {
    render(<TraceScrubber trace={trace} />);

    expect(screen.getByTestId("trace-frame-detail")).toHaveTextContent(
      "refund_policy_2026.pdf#p4",
    );
    fireEvent.change(screen.getByTestId("trace-scrubber-range"), {
      target: { value: "1" },
    });
    expect(screen.getByTestId("trace-frame-detail")).toHaveTextContent(
      "tool.lookup_order is executing",
    );
  });

  it("queues fork and save actions from the selected frame", () => {
    render(<TraceScrubber trace={trace} />);

    fireEvent.click(screen.getByTestId("trace-scrubber-fork"));
    expect(screen.getByTestId("trace-scrubber-action")).toHaveTextContent(
      "Fork from span_context",
    );
    fireEvent.click(screen.getByTestId("trace-scrubber-save"));
    expect(screen.getByTestId("trace-scrubber-action")).toHaveTextContent(
      "Save span_context",
    );
  });

  it("renders an explicit empty state when no frames exist", () => {
    render(<TraceScrubber trace={{ id: "empty", spans: [] }} />);

    expect(screen.getByTestId("state-panel")).toHaveTextContent(
      "Trace scrubber unavailable",
    );
    expect(screen.getByText(/no spans/)).toBeInTheDocument();
  });
});

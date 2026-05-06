import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";

import { AgentXrayPanel } from "./agent-xray-panel";
import type { Trace } from "@/lib/traces";

const trace: Trace = {
  id: "trace_refund_742",
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
      attributes: { source: "refund_policy_2026.pdf", retrieved_chunks: 2 },
      events: [],
    },
    {
      id: "span_tool",
      parent_id: null,
      name: "tool.lookup_order",
      category: "tool",
      kind: "client",
      service: "tool",
      start_ns: 100,
      end_ns: 200,
      status: "ok",
      attributes: { tool: "lookup_order" },
      events: [],
    },
  ],
};

describe("AgentXrayPanel", () => {
  it("renders representative trace evidence for every claim", () => {
    render(<AgentXrayPanel trace={trace} />);

    expect(screen.getByTestId("agent-xray")).toHaveTextContent(
      "Observed behavior",
    );
    expect(screen.getByTestId("agent-xray")).toHaveTextContent(
      "refund_policy_2026.pdf",
    );
    expect(
      screen.getAllByTestId("xray-representative-trace")[0],
    ).toHaveTextContent("trace_refund_742");
    expect(screen.getByTestId("agent-xray")).toHaveTextContent("unsupported");
  });

  it("shows an empty state instead of invented claims", () => {
    render(<AgentXrayPanel trace={{ id: "empty", spans: [] }} />);

    expect(screen.getByTestId("state-panel")).toHaveTextContent(
      "Agent X-Ray unavailable",
    );
  });
});

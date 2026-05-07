import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createAgentMapData,
  createAgentMapDataFromVersion,
  createEmptyAgentMapData,
  evaluateAgentMapEdit,
  INVALID_AGENT_MAP_EDIT,
} from "./agent-map-data";
import { AgentMap } from "./agent-map";

describe("AgentMap", () => {
  it("renders a comprehension-first map with inspector evidence and coverage", () => {
    render(<AgentMap data={createAgentMapData("agent_support")} />);

    expect(screen.getByTestId("agent-map")).toHaveTextContent("Agent map");
    expect(screen.getByTestId("agent-map-canvas")).toHaveTextContent(
      "Comprehension map",
    );
    expect(screen.getByTestId("agent-map")).toHaveTextContent(
      "Dependency coverage",
    );
    expect(screen.getByTestId("agent-map-inspector")).toHaveTextContent(
      "Chat and voice turns",
    );
    expect(
      screen.getByTestId("agent-map-inspector-evidence"),
    ).toHaveTextContent("trace_refund_742");
    expect(
      screen.getByText("Map is a lens, not the source of logic"),
    ).toBeInTheDocument();
  });

  it("opens the same inspector from the accessible list view", () => {
    render(<AgentMap data={createAgentMapData("agent_support")} />);

    fireEvent.click(screen.getByTestId("agent-map-view-list"));
    expect(screen.getByTestId("agent-map-list-view")).toHaveTextContent(
      "Accessible list view",
    );
    fireEvent.click(screen.getByTestId("agent-map-list-inspect-tool-refund"));
    expect(screen.getByTestId("agent-map-inspector")).toHaveTextContent(
      "issue_refund",
    );
    fireEvent.click(screen.getByTestId("agent-map-inspector-tab-history"));
    expect(screen.getByTestId("agent-map-inspector")).toHaveTextContent(
      "Mutating tool grants require preview",
    );
  });

  it("rejects invalid circular edits before the map changes", () => {
    const data = createAgentMapData("agent_support");
    expect(evaluateAgentMapEdit(data, INVALID_AGENT_MAP_EDIT)).toMatchObject({
      accepted: false,
    });

    render(<AgentMap data={data} />);
    fireEvent.click(screen.getByTestId("agent-map-invalid-edit"));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Invalid edit rejected",
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "hazard_circular_dependency",
    );
  });

  it("stages a fork preview from a trace-backed node", () => {
    render(<AgentMap data={createAgentMapData("agent_support")} />);

    fireEvent.click(screen.getByTestId("agent-map-node-output-answer"));
    fireEvent.click(screen.getByTestId("agent-map-fork"));
    expect(screen.getByTestId("agent-map-fork-notice")).toHaveTextContent(
      "fork/trace_refund_742-may-policy",
    );
    expect(screen.getByTestId("agent-map-fork-notice")).toHaveTextContent(
      "snap_refund_may",
    );
  });

  it("renders an empty and degraded state when instrumentation is unavailable", () => {
    render(<AgentMap data={createEmptyAgentMapData("agent_empty")} />);

    expect(screen.getByText("Map data is degraded")).toBeInTheDocument();
    expect(screen.getByText("No map instrumentation yet")).toBeInTheDocument();
    expect(screen.getByTestId("agent-map-invalid-edit")).toBeDisabled();
    expect(screen.getByText("No object selected")).toBeInTheDocument();
  });

  it("builds the comprehension map from a live agent version spec", () => {
    const data = createAgentMapDataFromVersion("agent_support", {
      id: "ver-live-map",
      agent_id: "agent_support",
      version: 7,
      deploy_state: "active",
      deployed_at: "2026-05-07T12:00:00Z",
      eval_status: "failed",
      promoted_to: "production",
      config_json: JSON.stringify({
        system_prompt: "Answer refund questions with policy evidence.",
        tools: ["lookup_order", "issue_refund"],
        memory_rules: ["preferred_language"],
        eval_suites: ["refund-regressions"],
      }),
    });

    expect(data.branch).toBe("v7");
    expect(data.objectState).toBe("production");
    expect(data.nodes.some((node) => node.label === "issue_refund")).toBe(true);
    expect(data.hazards.map((hazard) => hazard.id)).toContain(
      "hazard-live-tool-grant",
    );
    expect(data.hazards.map((hazard) => hazard.id)).toContain(
      "hazard-eval-regression",
    );
  });
});

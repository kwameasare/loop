import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createBuildToTestFlowData,
  createProductionBlockedBuildFlowData,
} from "@/lib/target-ux/build-flow";

import { BuildToTestFlow } from "./build-to-test-flow";

describe("BuildToTestFlow", () => {
  it("renders preview, fork, save-as-eval, branch state, and production guard", () => {
    render(
      <BuildToTestFlow
        data={createBuildToTestFlowData("agent_support", "agent")}
      />,
    );

    expect(screen.getByTestId("build-to-test-flow-agent")).toHaveTextContent(
      "Preview, fork, and save as eval",
    );
    expect(screen.getByTestId("build-to-test-flow-agent")).toHaveTextContent(
      "draft/refund-clarity",
    );
    expect(screen.getByTestId("build-to-test-flow-agent")).toHaveTextContent(
      "fork/trace_refund_742-turn-3",
    );
    expect(screen.getByTestId("build-flow-action-preview")).toHaveTextContent(
      "Preview draft",
    );
    expect(screen.getByTestId("build-flow-action-fork")).toHaveTextContent(
      "Fork from turn",
    );
    expect(screen.getByTestId("build-flow-action-save-eval")).toHaveTextContent(
      "Save run as eval",
    );
    expect(screen.getByTestId("build-flow-production-guard")).toHaveTextContent(
      "production traffic continues on the deployed version",
    );
    expect(screen.getByTestId("build-flow-production-action")).toBeDisabled();
  });

  it("switches action evidence for fork and save-as-eval", () => {
    render(
      <BuildToTestFlow
        data={createBuildToTestFlowData("agent_support", "behavior")}
      />,
    );

    fireEvent.click(screen.getByTestId("build-flow-action-fork"));
    expect(screen.getByTestId("build-flow-result")).toHaveTextContent(
      "Fork branch created",
    );
    expect(screen.getByTestId("build-flow-result")).toHaveTextContent(
      "exact agent, tool, KB, model, and memory state",
    );

    fireEvent.click(screen.getByTestId("build-flow-action-save-eval"));
    expect(screen.getByTestId("build-flow-result")).toHaveTextContent(
      "Eval case staged",
    );
    expect(screen.getByTestId("build-flow-result")).toHaveTextContent(
      "trace, tool, retrieval, memory, cost, and latency diffs",
    );
  });

  it("keeps production-protected objects blocked without hiding fork/eval controls", () => {
    render(
      <BuildToTestFlow
        data={createProductionBlockedBuildFlowData("agent_support", "behavior")}
      />,
    );

    expect(screen.getByText("Production edit locked")).toBeInTheDocument();
    expect(screen.getByTestId("build-flow-production-action")).toBeDisabled();
    expect(screen.getByTestId("build-flow-action-fork")).toBeEnabled();
    expect(screen.getByTestId("build-flow-action-save-eval")).toBeEnabled();
    expect(screen.getByTestId("build-to-test-flow-behavior")).toHaveTextContent(
      "Production",
    );
  });
});

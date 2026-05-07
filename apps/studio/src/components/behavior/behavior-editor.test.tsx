import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  createBehaviorEditorData,
  createBehaviorEditorDataFromVersion,
  createEmptyBehaviorEditorData,
} from "@/lib/behavior";

import { BehaviorEditor } from "./behavior-editor";

describe("BehaviorEditor", () => {
  it("renders the behavior surface with three modes, semantic diff, eval coverage, and preview", () => {
    render(<BehaviorEditor data={createBehaviorEditorData("agent_support")} />);

    expect(screen.getByTestId("behavior-editor")).toHaveTextContent(
      "Behavior editor",
    );
    expect(screen.getByTestId("behavior-mode-plain")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("behavior-plain-mode")).toHaveTextContent(
      "Resolve order, refund, and escalation questions",
    );
    expect(screen.getByTestId("behavior-semantic-diff")).toHaveTextContent(
      "You made cancellation answers cite the May 2026 refund policy",
    );
    expect(
      screen.getByRole("meter", { name: "Eval coverage" }),
    ).toHaveAttribute("aria-valuenow", "96");
    expect(screen.getByTestId("behavior-preview")).toHaveTextContent(
      "Preview before apply",
    );
    expect(screen.getByTestId("build-to-test-flow-behavior")).toHaveTextContent(
      "Preview, fork, and save as eval",
    );
    expect(screen.getByTestId("build-to-test-flow-behavior")).toHaveTextContent(
      "Save run as eval",
    );

    fireEvent.click(screen.getByTestId("behavior-mode-policy"));
    expect(screen.getByTestId("behavior-policy-mode")).toHaveTextContent(
      "Escalate legal threats",
    );
    expect(screen.getByTestId("behavior-mode-policy")).toHaveAttribute(
      "aria-selected",
      "true",
    );

    fireEvent.click(screen.getByTestId("behavior-mode-config"));
    expect(screen.getByTestId("behavior-config-mode")).toHaveTextContent(
      "lookup_order: read_only",
    );
    expect(screen.getByTestId("behavior-mode-config")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("shows inline risk flags and sentence telemetry with evidence", () => {
    render(<BehaviorEditor data={createBehaviorEditorData("agent_support")} />);

    const sentence = screen.getByTestId(
      "behavior-sentence-sentence_purpose_cancel",
    );
    expect(sentence).toHaveTextContent("Missing eval coverage");
    fireEvent.mouseEnter(sentence);

    const telemetry = screen.getByTestId("behavior-sentence-telemetry");
    expect(telemetry).toHaveTextContent("Cited");
    expect(telemetry).toHaveTextContent("31 outputs over 7 days");
    expect(telemetry).toHaveTextContent("eval_refunds refund_window_es_may");
    expect(screen.getByTestId("behavior-risk-flags")).toHaveTextContent(
      "Tool grant risk",
    );
    expect(screen.getByTestId("style-transfer-panel")).toHaveTextContent(
      "Same policy, different tone",
    );
  });

  it("previews style-transfer rewrites with eval deltas", async () => {
    render(<BehaviorEditor data={createBehaviorEditorData("agent_support")} />);

    fireEvent.click(screen.getByTestId("style-transfer-run"));

    expect(await screen.findByTestId("style-transfer-results")).toHaveTextContent(
      "formal voice",
    );
  });

  it("keeps apply blocked until preview policy checks pass", () => {
    render(<BehaviorEditor data={createBehaviorEditorData("agent_support")} />);

    expect(screen.getByTestId("behavior-preview-blocked")).toHaveTextContent(
      "Release Manager approval",
    );
    expect(screen.getByTestId("behavior-apply-draft")).toBeDisabled();
    expect(screen.getByTestId("behavior-run-preview")).toBeEnabled();
  });

  it("renders a useful empty state when no behavior sections exist", () => {
    render(
      <BehaviorEditor data={createEmptyBehaviorEditorData("agent_empty")} />,
    );

    expect(screen.getByText("No behavior sections yet")).toBeInTheDocument();
    expect(screen.getByText("No semantic diff yet")).toBeInTheDocument();
    expect(screen.getByTestId("behavior-apply-draft")).toBeDisabled();
    expect(screen.getByTestId("behavior-risk-flags")).toHaveTextContent(
      "No risk flags yet",
    );
  });

  it("renders behavior sourced from a live agent version spec", () => {
    const data = createBehaviorEditorDataFromVersion("agent_support", {
      id: "ver-live",
      agent_id: "agent_support",
      version: 3,
      deploy_state: "active",
      deployed_at: "2026-05-07T12:00:00Z",
      eval_status: "passed",
      config_json: JSON.stringify({
        system_prompt: "Answer refund questions. Escalate legal threats.",
        tools: ["lookup_order"],
      }),
      promoted_to: "production",
    });

    render(<BehaviorEditor data={data} />);

    expect(screen.getByText("System prompt")).toBeInTheDocument();
    expect(screen.getAllByText(/Answer refund questions/).length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("Declared tools")).toBeInTheDocument();
  });
});

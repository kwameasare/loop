import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createBehaviorEditorData } from "@/lib/behavior";

import { FailureRepairLoopPanel } from "./failure-repair-loop-panel";

describe("FailureRepairLoopPanel", () => {
  it("turns a selected observed behavior failure into a regression eval", async () => {
    const sentence =
      createBehaviorEditorData("agent_support").sections[0]!.sentences[0]!;
    const saveEval = vi.fn(async () => ({
      ok: true,
      suite_id: "suite_observed",
      case_id: "case_observed",
    }));

    render(
      <FailureRepairLoopPanel
        agentId="agent_support"
        sentence={sentence}
        saveEval={saveEval}
      />,
    );

    expect(screen.getByTestId("failure-repair-loop")).toHaveTextContent(
      "90-second loop",
    );
    expect(screen.getByTestId("failure-repair-loop")).toHaveTextContent(
      "Regression spec",
    );

    fireEvent.click(screen.getByTestId("failure-repair-save-eval"));

    expect(await screen.findByTestId("failure-repair-saved")).toHaveTextContent(
      "case_observed",
    );
    expect(saveEval).toHaveBeenCalledWith(
      "agent_support",
      expect.objectContaining({
        sentence_id: sentence.id,
        sentence_text: sentence.text,
        expected_outcome: expect.stringContaining(sentence.text),
        proposed_fix: expect.stringContaining("Tighten the behavior rule"),
      }),
    );
  });

  it("renders an empty repair state when no sentence is selected", () => {
    render(<FailureRepairLoopPanel agentId="agent_support" sentence={null} />);

    expect(screen.getByText("Select a sentence to repair")).toBeInTheDocument();
  });
});

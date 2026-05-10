import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { createBehaviorEditorData } from "@/lib/behavior";
import { targetUxFixtures } from "@/lib/target-ux";

import { FailureRepairLoopPanel } from "./failure-repair-loop-panel";

describe("FailureRepairLoopPanel", () => {
  it("turns a selected observed behavior failure into a regression eval", async () => {
    const sentence = createBehaviorEditorData("agent_support", targetUxFixtures)
      .sections[0]!.sentences[0]!;
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

  it("generates a focused fix and replay summary before saving eval", async () => {
    const sentence = createBehaviorEditorData("agent_support", targetUxFixtures)
      .sections[0]!.sentences[1]!;
    const requestRepair = vi.fn(async () => ({
      id: "repair_1",
      workspace_id: "ws_1",
      agent_id: "agent_support",
      target_object: {
        kind: "behavior_sentence",
        id: sentence.id,
        label: "Responsible behavior sentence",
      },
      proposal: {
        title: "Tighten behavior for cancellation policy",
        diff: "Require current May policy citation before refund windows.",
        rationale: "Archived policy was cited.",
        evidence_ref: "trace_refund_742",
      },
      replay: {
        draft_ref: "replay/sentence_purpose_cancel/nearby-turns",
        improved: 3,
        unchanged: 1,
        regressed: 0,
        needs_review: 1,
        examples: [],
      },
      next_actions: ["accept_or_edit_fix", "save_regression_eval"],
      evidence_refs: ["trace_refund_742", sentence.id],
    }));
    const saveEval = vi.fn(async () => ({
      ok: true,
      suite_id: "suite_observed",
      case_id: "case_observed",
    }));
    const decideRepair = vi.fn(async () => ({
      ok: true,
      id: "decision_1",
      proposal_id: "repair_1",
      status: "edited" as const,
      accepted_diff:
        "Require current May policy citation before refund windows.",
      draft_ref: "replay/sentence_purpose_cancel/nearby-turns",
      audit_ref: "audit/repair_1/decision_1",
      next_actions: ["save_regression_eval"],
      evidence_refs: ["trace_refund_742", sentence.id],
    }));

    render(
      <FailureRepairLoopPanel
        agentId="agent_support"
        sentence={sentence}
        requestRepair={requestRepair}
        saveEval={saveEval}
        decideRepair={decideRepair}
      />,
    );

    fireEvent.click(screen.getByTestId("failure-repair-generate"));

    expect(
      await screen.findByTestId("failure-repair-proposal"),
    ).toHaveTextContent("Regressed");
    expect(screen.getByTestId("failure-repair-proposal")).toHaveTextContent(
      "0",
    );

    fireEvent.change(screen.getByTestId("failure-repair-edit"), {
      target: {
        value: "Require current May policy citation before refund windows.",
      },
    });
    fireEvent.click(screen.getByTestId("failure-repair-accept-edit"));

    expect(
      await screen.findByTestId("failure-repair-decision"),
    ).toHaveTextContent(
      "Require current May policy citation before refund windows.",
    );
    expect(decideRepair).toHaveBeenCalledWith(
      "agent_support",
      "repair_1",
      expect.objectContaining({
        decision: "edited",
        sentence_id: sentence.id,
        proposal_diff:
          "Require current May policy citation before refund windows.",
        edited_diff:
          "Require current May policy citation before refund windows.",
        replay_ref: "replay/sentence_purpose_cancel/nearby-turns",
      }),
    );

    fireEvent.click(screen.getByTestId("failure-repair-save-eval"));

    await screen.findByTestId("failure-repair-saved");
    expect(saveEval).toHaveBeenCalledWith(
      "agent_support",
      expect.objectContaining({
        proposed_fix:
          "Require current May policy citation before refund windows.",
        replay_ref: "replay/sentence_purpose_cancel/nearby-turns",
      }),
    );
  });

  it("renders an empty repair state when no sentence is selected", () => {
    render(<FailureRepairLoopPanel agentId="agent_support" sentence={null} />);

    expect(screen.getByText("Select a sentence to repair")).toBeInTheDocument();
  });

  it("surfaces backend-required errors instead of generating local repairs", async () => {
    const originalBaseUrl = process.env.LOOP_CP_API_BASE_URL;
    process.env.LOOP_CP_API_BASE_URL = "";
    const sentence = createBehaviorEditorData("agent_support", targetUxFixtures)
      .sections[0]!.sentences[0]!;

    try {
      render(
        <FailureRepairLoopPanel agentId="agent_support" sentence={sentence} />,
      );

      fireEvent.click(screen.getByTestId("failure-repair-generate"));

      expect(
        await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("failure-repair-proposal"),
      ).not.toBeInTheDocument();
    } finally {
      process.env.LOOP_CP_API_BASE_URL = originalBaseUrl;
    }
  });
});

import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { AdversarialCatch } from "@/lib/adversarial-catches";
import type { BehaviorSentence } from "@/lib/behavior";

import { AdversarialCatchPanel } from "./adversarial-catch-panel";

const SENTENCE: BehaviorSentence = {
  id: "sentence_refund_cap",
  role: "promise",
  text: "Never approve refunds over $500.",
  tokenCount: 5,
  telemetry: {
    citedOutputs7d: 47,
    contradictedTraces: 3,
    neverInvokedTurns: 12,
    evalCases: 4,
    evidence: "trace_refund_742 eval_refunds",
    confidence: "medium",
  },
  riskIds: ["refund_cap_risk"],
};

const CATCH: AdversarialCatch = {
  id: "catch_refund_cap",
  workspace_id: "workspace_1",
  agent_id: "agent_support",
  probe_run_id: "probe_refund_cap",
  rule_id: SENTENCE.id,
  rule_text: SENTENCE.text,
  question:
    'You said "never approve refunds over $500." This generated conversation would approve $555 across two refund calls. Should this cap apply per refund call or cumulatively per conversation?',
  generated_scenario:
    "User requests two refunds of $275 and $280 in the same conversation.",
  evidence_ref: "adversarial_probe/probe_refund_cap/sentence_refund_cap",
  risk_class: "high",
  status: "open",
  resolution: null,
  eval_case_refs: [],
  created_at: "2026-05-09T00:00:00Z",
  updated_at: "2026-05-09T00:00:00Z",
};

describe("AdversarialCatchPanel", () => {
  it("asks the catch question and resolves it into eval cases", async () => {
    const runProbe = vi.fn(async () => ({
      run: {
        id: "probe_refund_cap",
        workspace_id: "workspace_1",
        agent_id: "agent_support",
        rule_id: SENTENCE.id,
        risk_class: "high" as const,
        budget_tokens: 2000,
        budget_tokens_used: 640,
        status: "completed" as const,
        created_by: "owner",
        created_at: "2026-05-09T00:00:00Z",
      },
      catches: [CATCH],
    }));
    const resolveCatch = vi.fn(async () => ({
      ...CATCH,
      status: "resolved" as const,
      eval_case_refs: [
        { suite_id: "suite_1", case_id: "case_accepted" },
        { suite_id: "suite_1", case_id: "case_rejected" },
      ],
      resolution: {
        intended_interpretation:
          "Apply the cap cumulatively across the whole conversation.",
        rejected_interpretation:
          "Do not allow multiple tool calls to bypass the cap.",
        dismiss_reason: "",
        created_by: "owner",
        created_at: "2026-05-09T00:00:00Z",
      },
    }));

    render(
      <AdversarialCatchPanel
        agentId="agent_support"
        sentence={SENTENCE}
        runProbe={runProbe}
        resolveCatch={resolveCatch}
      />,
    );

    fireEvent.click(screen.getByTestId("run-adversarial-probe"));

    expect(
      await screen.findByTestId("adversarial-catch-question"),
    ).toHaveTextContent("cumulatively");
    expect(runProbe).toHaveBeenCalledWith(
      "agent_support",
      expect.objectContaining({
        rule_id: SENTENCE.id,
        rule_text: SENTENCE.text,
        risk_class: "high",
      }),
    );

    fireEvent.change(screen.getByTestId("catch-intended"), {
      target: { value: "Cap applies cumulatively per conversation." },
    });
    fireEvent.change(screen.getByTestId("catch-rejected"), {
      target: { value: "Cap applies only per tool call." },
    });
    fireEvent.click(screen.getByTestId("resolve-adversarial-catch"));

    expect(
      await screen.findByTestId("adversarial-catch-result"),
    ).toHaveTextContent("2 eval cases");
    expect(resolveCatch).toHaveBeenCalledWith(
      "agent_support",
      "catch_refund_cap",
      expect.objectContaining({
        intended_interpretation: "Cap applies cumulatively per conversation.",
        rejected_interpretation: "Cap applies only per tool call.",
        create_eval_cases: true,
      }),
    );
  });

  it("renders an empty state until a behavior sentence is selected", () => {
    render(<AdversarialCatchPanel agentId="agent_support" sentence={null} />);

    expect(screen.getByText("Select a sentence to probe")).toBeInTheDocument();
  });
});

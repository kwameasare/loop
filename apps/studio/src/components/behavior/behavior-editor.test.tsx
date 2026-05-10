import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createBehaviorEditorData,
  createBehaviorEditorDataFromVersion,
  createEmptyBehaviorEditorData,
} from "@/lib/behavior";
import { targetUxFixtures } from "@/lib/target-ux";

import { BehaviorEditor } from "./behavior-editor";

describe("BehaviorEditor", () => {
  const previousBaseUrl = process.env.LOOP_CP_API_BASE_URL;

  async function waitForCatchPanelToSettle() {
    const panel = screen.queryByTestId("adversarial-catch-panel");
    if (!panel) return;
    await waitFor(() =>
      expect(panel).not.toHaveTextContent(
        "Checking persisted catches for this rule",
      ),
    );
  }

  afterEach(() => {
    process.env.LOOP_CP_API_BASE_URL = previousBaseUrl;
    vi.unstubAllGlobals();
  });

  it("renders the behavior surface with three modes, semantic diff, eval coverage, and preview", async () => {
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

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
    expect(
      screen.queryByTestId("build-to-test-flow-behavior"),
    ).not.toBeInTheDocument();

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
    await waitForCatchPanelToSettle();
  });

  it("shows inline risk flags and sentence telemetry with evidence", async () => {
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

    const sentence = screen.getByTestId(
      "behavior-sentence-sentence_purpose_cancel",
    );
    expect(sentence).toHaveTextContent("Missing eval coverage");
    fireEvent.mouseEnter(sentence);
    expect(
      screen.getByTestId("behavior-context-actions-sentence_purpose_cancel"),
    ).toHaveTextContent("Explain");
    expect(
      screen.getByTestId("behavior-context-actions-sentence_purpose_cancel"),
    ).toHaveTextContent("Show source");
    expect(
      screen.getByTestId("behavior-context-actions-sentence_purpose_cancel"),
    ).toHaveTextContent("Fix this");
    expect(
      screen.getByTestId("behavior-context-actions-sentence_purpose_cancel"),
    ).toHaveTextContent("Save as eval");
    fireEvent.click(
      screen.getByTestId("behavior-action-show-source-sentence_purpose_cancel"),
    );
    expect(
      screen.getByTestId("behavior-selection-action-panel"),
    ).toHaveTextContent("Stable source reference");
    expect(
      screen.getByTestId("behavior-selection-action-panel"),
    ).toHaveTextContent("trace/sentence_purpose_cancel");

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
    expect(screen.getByTestId("failure-repair-loop")).toHaveTextContent(
      "Save failure as eval",
    );
    expect(screen.getByTestId("adversarial-catch-panel")).toHaveTextContent(
      "Ask the calm adversarial question",
    );
    await waitForCatchPanelToSettle();
  });

  it("uses the selected sentence action menu to generate the focused repair", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        id: "repair_1",
        workspace_id: "ws_1",
        agent_id: "agent_support",
        target_object: {
          kind: "knowledge_chunk",
          id: "sentence_purpose_cancel",
          label: "Responsible knowledge source",
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
        evidence_refs: ["trace_refund_742", "sentence_purpose_cancel"],
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.mouseEnter(
      screen.getByTestId("behavior-sentence-sentence_purpose_cancel"),
    );
    fireEvent.click(
      screen.getByTestId("behavior-action-fix-this-sentence_purpose_cancel"),
    );

    expect(
      screen.getByTestId("behavior-selection-action-panel"),
    ).toHaveTextContent("Repair target opened");
    expect(
      await screen.findByTestId("failure-repair-proposal"),
    ).toHaveTextContent("Tighten behavior for cancellation policy");
    const [, init] = fetcher.mock.calls.find(([url]) =>
      String(url).includes("/behavior/repair-proposals"),
    )!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      sentence_id: "sentence_purpose_cancel",
      sentence_role: "promise",
      target_object_kind: "knowledge_chunk",
      risk_tags: ["risk_eval_gap"],
    });
    await waitForCatchPanelToSettle();
  });

  it("opens directly on a linked behavior sentence", async () => {
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
        initialSelectedSentenceId="sentence_purpose_cancel"
      />,
    );

    expect(
      screen.getByTestId("behavior-context-actions-sentence_purpose_cancel"),
    ).toHaveTextContent("Fix this");
    expect(screen.getByTestId("behavior-sentence-telemetry")).toHaveTextContent(
      "When a customer asks to cancel, cite the May 2026 refund policy",
    );
    expect(screen.getByTestId("failure-repair-loop")).toHaveTextContent(
      "Selected failure",
    );
    await waitForCatchPanelToSettle();
  });

  it("previews style-transfer rewrites with eval deltas", async () => {
    process.env.LOOP_CP_API_BASE_URL = "https://cp.test";
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        items: [
          {
            voice: "formal",
            rewrite: "Answer refund questions with a formal policy citation.",
            eval_delta: 0.02,
            evidence_ref: "style-transfer/agent_support/formal",
          },
        ],
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("style-transfer-run"));

    expect(
      await screen.findByTestId("style-transfer-results"),
    ).toHaveTextContent("formal voice");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agent_support/style-transfer",
      expect.objectContaining({ method: "POST" }),
    );
    await waitForCatchPanelToSettle();
  });

  it("requires backend style-transfer before showing voice rewrites", async () => {
    process.env.LOOP_CP_API_BASE_URL = "";
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

    fireEvent.click(screen.getByTestId("style-transfer-run"));

    expect(
      await screen.findByText(/LOOP_CP_API_BASE_URL is required/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("style-transfer-results"),
    ).not.toBeInTheDocument();
    await waitForCatchPanelToSettle();
  });

  it("keeps apply blocked until preview policy checks pass", async () => {
    render(
      <BehaviorEditor
        data={createBehaviorEditorData("agent_support", targetUxFixtures)}
      />,
    );

    expect(screen.getByTestId("behavior-preview-blocked")).toHaveTextContent(
      "Release Manager approval",
    );
    expect(screen.getByTestId("behavior-apply-draft")).toBeDisabled();
    expect(screen.getByTestId("behavior-run-preview")).toBeEnabled();
    await waitForCatchPanelToSettle();
  });

  it("renders a useful empty state when no behavior sections exist", () => {
    const data = createEmptyBehaviorEditorData("agent_empty");
    render(<BehaviorEditor data={data} />);

    expect(screen.getByText("No behavior sections yet")).toBeInTheDocument();
    expect(screen.getByText("No semantic diff yet")).toBeInTheDocument();
    expect(screen.getByTestId("behavior-apply-draft")).toBeDisabled();
    expect(screen.getByTestId("behavior-risk-flags")).toHaveTextContent(
      "No risk flags yet",
    );
    expect(data.agentName).toBe("Agent agent_empty");
    expect(
      screen.queryByText("Acme Support Concierge"),
    ).not.toBeInTheDocument();
  });

  it("renders behavior sourced from a live agent version spec", async () => {
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
    expect(
      screen.getAllByText(/Answer refund questions/).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("Declared tools")).toBeInTheDocument();
    await waitForCatchPanelToSettle();
  });
});

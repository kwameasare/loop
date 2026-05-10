import { describe, expect, it, vi } from "vitest";

import {
  decideObservedFailureRepair,
  requestObservedFailureRepair,
  saveObservedFailureEval,
} from "./behavior-repair";

const INPUT = {
  sentence_id: "sentence_purpose_cancel",
  sentence_text: "Cite the May 2026 policy before refund windows.",
  sentence_role: "promise",
  trace_id: "trace_refund_742",
  failure_reason: "The production answer cited the archived policy.",
  expected_outcome: "The answer cites the current May 2026 refund policy.",
  proposed_fix:
    "Require current policy citation before quoting refund windows.",
  replay_ref: "replay/run/trace_refund_742/fixed",
  channel: "web_chat",
  version_ref: "version/v23",
  risk_tags: ["risk_eval_gap"],
  target_object_kind: "knowledge_chunk",
};

describe("behavior repair client", () => {
  it("does not fabricate repair proposals or eval cases without cp-api", async () => {
    await expect(
      requestObservedFailureRepair("agt_1", INPUT, { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      saveObservedFailureEval("agt_1", INPUT, { baseUrl: "" }),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");

    await expect(
      decideObservedFailureRepair(
        "agt_1",
        "repair_1",
        {
          decision: "accepted",
          sentence_id: INPUT.sentence_id,
          trace_id: INPUT.trace_id,
          proposal_diff: INPUT.proposed_fix,
          replay_ref: INPUT.replay_ref,
        },
        { baseUrl: "" },
      ),
    ).rejects.toThrow("LOOP_CP_API_BASE_URL is required");
  });

  it("keeps deterministic repair proposals explicitly opt-in", async () => {
    const response = await requestObservedFailureRepair("agt_1", INPUT, {
      baseUrl: "",
      allowFixture: true,
    });

    expect(response.target_object.kind).toBe("knowledge_chunk");
    expect(response.proposal.evidence_ref).toBe(INPUT.trace_id);
    expect(response.replay).toMatchObject({
      improved: 3,
      regressed: 0,
    });
    expect(response.next_actions).toContain("save_regression_eval");
  });

  it("keeps deterministic observed-failure eval cases explicitly opt-in", async () => {
    const response = await saveObservedFailureEval("agt_1", INPUT, {
      baseUrl: "",
      allowFixture: true,
    });

    expect(response.ok).toBe(true);
    expect(response.case_id).toBe("case_sentence_purpose_cancel");
    expect(response.case?.source).toBe("behavior-fix");
    expect(response.case?.expected).toMatchObject({
      proposed_fix: INPUT.proposed_fix,
    });
  });

  it("keeps deterministic repair decisions explicitly opt-in", async () => {
    const response = await decideObservedFailureRepair(
      "agt_1",
      "repair_1",
      {
        decision: "edited",
        sentence_id: INPUT.sentence_id,
        trace_id: INPUT.trace_id,
        proposal_diff: INPUT.proposed_fix,
        edited_diff: "Use the current policy before answering.",
        replay_ref: INPUT.replay_ref,
        evidence_refs: [INPUT.sentence_id],
      },
      { baseUrl: "", allowFixture: true },
    );

    expect(response.status).toBe("edited");
    expect(response.accepted_diff).toBe(
      "Use the current policy before answering.",
    );
    expect(response.next_actions).toContain("save_regression_eval");
    expect(response.evidence_refs).toContain(INPUT.trace_id);
  });

  it("posts observed failures to the agent-scoped eval endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ok: true,
        suite_id: "suite_1",
        case_id: "case_1",
      }),
    );

    const response = await saveObservedFailureEval("agt_1", INPUT, {
      baseUrl: "https://cp.test",
      fetcher,
      token: "tok",
    });

    expect(response.case_id).toBe("case_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/eval-cases/from-observed-failure",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      sentence_id: INPUT.sentence_id,
      sentence_role: INPUT.sentence_role,
      trace_id: INPUT.trace_id,
      proposed_fix: INPUT.proposed_fix,
      channel: INPUT.channel,
      version_ref: INPUT.version_ref,
      risk_tags: INPUT.risk_tags,
      target_object_kind: INPUT.target_object_kind,
    });
  });

  it("posts observed repair requests to the behavior repair endpoint", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        id: "repair_1",
        workspace_id: "ws_1",
        agent_id: "agt_1",
        target_object: {
          kind: "behavior_sentence",
          id: INPUT.sentence_id,
          label: "Responsible behavior sentence",
        },
        proposal: {
          title: "Tighten behavior",
          diff: "Require current policy citation.",
          rationale: INPUT.failure_reason,
          evidence_ref: INPUT.trace_id,
        },
        replay: {
          draft_ref: INPUT.replay_ref,
          improved: 2,
          unchanged: 1,
          regressed: 0,
          needs_review: 1,
          examples: [],
        },
        next_actions: ["accept_or_edit_fix", "save_regression_eval"],
        evidence_refs: [INPUT.trace_id],
      }),
    );

    const response = await requestObservedFailureRepair("agt_1", INPUT, {
      baseUrl: "https://cp.test",
      fetcher,
      token: "tok",
    });

    expect(response.id).toBe("repair_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/behavior/repair-proposals",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      sentence_id: INPUT.sentence_id,
      sentence_role: INPUT.sentence_role,
      trace_id: INPUT.trace_id,
      replay_ref: INPUT.replay_ref,
      risk_tags: INPUT.risk_tags,
      target_object_kind: INPUT.target_object_kind,
    });
  });

  it("posts repair proposal decisions before eval creation", async () => {
    const fetcher = vi.fn<typeof fetch>(async () =>
      Response.json({
        ok: true,
        id: "decision_1",
        proposal_id: "repair_1",
        status: "accepted",
        accepted_diff: INPUT.proposed_fix,
        draft_ref: INPUT.replay_ref,
        audit_ref: "audit/repair_1",
        next_actions: ["save_regression_eval"],
        evidence_refs: [INPUT.trace_id, INPUT.replay_ref],
      }),
    );

    const response = await decideObservedFailureRepair(
      "agt_1",
      "repair_1",
      {
        decision: "accepted",
        sentence_id: INPUT.sentence_id,
        trace_id: INPUT.trace_id,
        proposal_diff: INPUT.proposed_fix,
        replay_ref: INPUT.replay_ref,
        evidence_refs: [INPUT.sentence_id],
        target_object_kind: INPUT.target_object_kind,
      },
      {
        baseUrl: "https://cp.test",
        fetcher,
        token: "tok",
      },
    );

    expect(response.id).toBe("decision_1");
    expect(fetcher).toHaveBeenCalledWith(
      "https://cp.test/v1/agents/agt_1/behavior/repair-proposals/repair_1/decision",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ authorization: "Bearer tok" }),
      }),
    );
    const [, init] = fetcher.mock.calls[0]!;
    expect(JSON.parse(String(init?.body))).toMatchObject({
      decision: "accepted",
      sentence_id: INPUT.sentence_id,
      trace_id: INPUT.trace_id,
      proposal_diff: INPUT.proposed_fix,
      replay_ref: INPUT.replay_ref,
      target_object_kind: INPUT.target_object_kind,
    });
  });
});

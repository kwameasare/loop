import { describe, expect, it } from "vitest";

import {
  FIXTURE_EVIDENCE_CONTEXT,
  ResolutionDraftError,
  buildEvalCaseFromResolution,
} from "./inbox-resolution";

describe("buildEvalCaseFromResolution", () => {
  it("links the trace, copies operator inputs, and attaches tool + retrieval evidence", () => {
    const c = buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
      outcome: "resolved",
      saveAsEval: true,
      expectedOutcome: "  Refund and email receipt  ",
      failureReason: "Tool flakiness",
    });
    expect(c.id).toBe("eval_thr_8823");
    expect(c.linkedTrace).toBe("trace/thr_8823");
    expect(c.expectedOutcome).toBe("Refund and email receipt");
    expect(c.failureReason).toBe("Tool flakiness");
    expect(c.source).toBe("operator-resolution");
    expect(c.attachments).toEqual([
      "tool/shopify-orders#thr_8823",
      "tool/refund-policy#thr_8823",
      "kb/refund-policy.md#section-2",
      "kb/escalation.md#tool-failure",
    ]);
  });

  it("throws when saveAsEval is false", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: false,
        expectedOutcome: "x",
        failureReason: "y",
      }),
    ).toThrow(ResolutionDraftError);
  });

  it("throws when expectedOutcome is blank", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: true,
        expectedOutcome: "   ",
        failureReason: "y",
      }),
    ).toThrow(/expectedOutcome/);
  });

  it("throws when failureReason is blank", () => {
    expect(() =>
      buildEvalCaseFromResolution(FIXTURE_EVIDENCE_CONTEXT, {
        outcome: "resolved",
        saveAsEval: true,
        expectedOutcome: "x",
        failureReason: "",
      }),
    ).toThrow(/failureReason/);
  });
});

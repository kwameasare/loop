import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConversationEvidence } from "./conversation-evidence";
import { ResolutionToEval } from "./resolution-to-eval";
import { SuggestedDraft } from "./suggested-draft";
import { FIXTURE_EVIDENCE_CONTEXT } from "@/lib/inbox-resolution";

describe("ConversationEvidence", () => {
  it("defaults to the trace pane and shows tool/error rows", () => {
    render(<ConversationEvidence ctx={FIXTURE_EVIDENCE_CONTEXT} />);
    expect(
      screen.getByTestId("conversation-evidence-pane-trace"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("evidence-trace-step_2")).toHaveTextContent(
      /Tool call/,
    );
  });

  it("switches to memory / tools / retrieval panes via tab clicks", () => {
    render(<ConversationEvidence ctx={FIXTURE_EVIDENCE_CONTEXT} />);
    fireEvent.click(screen.getByTestId("conversation-evidence-tab-memory"));
    expect(screen.getByTestId("evidence-memory-mem_1")).toHaveTextContent(
      /vip_tier/,
    );
    fireEvent.click(screen.getByTestId("conversation-evidence-tab-tools"));
    expect(screen.getByTestId("evidence-tool-tool_1")).toHaveTextContent(
      /ShopifyOrders\.read/,
    );
    fireEvent.click(screen.getByTestId("conversation-evidence-tab-retrieval"));
    expect(screen.getByTestId("evidence-retrieval-rtv_1")).toHaveTextContent(
      /refund-policy\.md/,
    );
  });
});

describe("SuggestedDraft", () => {
  it("calls onInsert with the (possibly edited) suggested text", () => {
    const onInsert = vi.fn();
    render(<SuggestedDraft draft="hello" onInsert={onInsert} />);
    const ta = screen.getByTestId(
      "suggested-draft-text",
    ) as HTMLTextAreaElement;
    fireEvent.change(ta, { target: { value: "hello world" } });
    fireEvent.click(screen.getByTestId("suggested-draft-insert"));
    expect(onInsert).toHaveBeenCalledWith("hello world");
  });

  it("hides itself once dismissed", () => {
    const onDismiss = vi.fn();
    render(
      <SuggestedDraft
        draft="hello"
        onInsert={() => {}}
        onDismiss={onDismiss}
      />,
    );
    fireEvent.click(screen.getByTestId("suggested-draft-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("suggested-draft")).toBeNull();
    expect(
      screen.getByTestId("suggested-draft-dismissed"),
    ).toBeInTheDocument();
  });
});

describe("ResolutionToEval", () => {
  it("disables save when expectedOutcome is blank", () => {
    render(
      <ResolutionToEval
        ctx={FIXTURE_EVIDENCE_CONTEXT}
        onSave={async () => ({ ok: true })}
        initialDraft={{
          outcome: "resolved",
          saveAsEval: true,
          expectedOutcome: "",
          failureReason: "tool flake",
        }}
      />,
    );
    expect(screen.getByTestId("resolution-save-eval")).toBeDisabled();
  });

  it("on save, calls onSave with linked trace + tool + retrieval attachments and shows audited confirmation", async () => {
    const onSave = vi.fn(async () => ({ ok: true, suite_id: "ops-evals" }));
    render(
      <ResolutionToEval ctx={FIXTURE_EVIDENCE_CONTEXT} onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("resolution-save-eval"));
    await screen.findByTestId("resolution-to-eval-saved");
    expect(onSave).toHaveBeenCalledTimes(1);
    const arg = onSave.mock.calls[0][0];
    expect(arg.linkedTrace).toBe("trace/thr_8823");
    expect(arg.attachments).toContain("tool/shopify-orders#thr_8823");
    expect(arg.attachments).toContain("kb/refund-policy.md#section-2");
    expect(arg.source).toBe("operator-resolution");
    expect(
      screen.getByTestId("resolution-to-eval-saved"),
    ).toHaveTextContent(/ops-evals/);
  });

  it("renders the failure path when the save handler returns ok=false", async () => {
    const onSave = vi.fn(async () => ({
      ok: false,
      error: "permission denied",
    }));
    render(
      <ResolutionToEval ctx={FIXTURE_EVIDENCE_CONTEXT} onSave={onSave} />,
    );
    fireEvent.click(screen.getByTestId("resolution-save-eval"));
    const err = await screen.findByTestId("resolution-to-eval-error");
    expect(err).toHaveTextContent(/permission denied/);
  });
});

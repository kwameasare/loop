import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { CommentThreadView } from "../comments/comment-thread";
import { ChangesetApprovals } from "./changeset-approvals";
import { PairDebugPanel } from "./pair-debug-panel";
import { PresenceBar } from "./presence-bar";

import { FIXTURE_THREADS } from "@/lib/comments";
import {
  FIXTURE_CHANGESET,
  FIXTURE_PAIR_DEBUG,
  FIXTURE_PRESENCE,
} from "@/lib/collaboration";

const ME = { id: "u_kojo", display: "Kojo A." };

describe("PresenceBar", () => {
  it("renders one entry per user", () => {
    render(<PresenceBar users={FIXTURE_PRESENCE} />);
    for (const u of FIXTURE_PRESENCE) {
      expect(screen.getByTestId(`presence-user-${u.id}`).textContent).toContain(
        u.display,
      );
    }
  });
});

describe("CommentThreadView", () => {
  it("flags stale anchor when version drifts", () => {
    const stale = FIXTURE_THREADS[1];
    render(<CommentThreadView thread={stale} currentUser={ME} />);
    expect(
      screen.getByTestId(`thread-stale-${stale.id}`),
    ).toBeInTheDocument();
  });

  it("resolves a thread into an eval spec and reports the input", () => {
    const fresh = FIXTURE_THREADS[0];
    const onResolve = vi.fn();
    render(
      <CommentThreadView
        thread={fresh}
        currentUser={ME}
        onResolveAsEval={onResolve}
      />,
    );
    fireEvent.change(screen.getByTestId(`thread-eval-input-${fresh.id}`), {
      target: { value: "eval_refund_callback" },
    });
    fireEvent.click(screen.getByTestId(`thread-resolve-btn-${fresh.id}`));
    expect(onResolve).toHaveBeenCalledWith(
      expect.objectContaining({
        threadId: fresh.id,
        evalSpecId: "eval_refund_callback",
        resolvedBy: "u_kojo",
      }),
    );
    expect(
      screen.getByTestId(`thread-resolved-${fresh.id}`).textContent,
    ).toContain("eval_refund_callback");
  });

  it("blocks resolution when eval spec id is empty", () => {
    const fresh = FIXTURE_THREADS[0];
    const onResolve = vi.fn();
    render(
      <CommentThreadView
        thread={fresh}
        currentUser={ME}
        onResolveAsEval={onResolve}
      />,
    );
    fireEvent.click(screen.getByTestId(`thread-resolve-btn-${fresh.id}`));
    expect(
      screen.getByTestId(`thread-error-${fresh.id}`).textContent,
    ).toContain("required");
    expect(onResolve).not.toHaveBeenCalled();
  });
});

describe("ChangesetApprovals", () => {
  it("renders approval pills for every axis with reviewer and rationale", () => {
    render(<ChangesetApprovals changeset={FIXTURE_CHANGESET} />);
    expect(screen.getByTestId("approval-behavior").textContent).toContain(
      "approved",
    );
    expect(screen.getByTestId("approval-cost").textContent).toContain(
      "p95 cost +18%",
    );
    expect(screen.getByTestId("approval-latency").textContent).toContain(
      "pending",
    );
  });

  it("disables merge until every axis is approved; ready when all green", () => {
    const onMerge = vi.fn();
    const { rerender } = render(
      <ChangesetApprovals changeset={FIXTURE_CHANGESET} onMerge={onMerge} />,
    );
    const btn = screen.getByTestId(
      `changeset-merge-${FIXTURE_CHANGESET.id}`,
    ) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    fireEvent.click(btn);
    expect(onMerge).not.toHaveBeenCalled();

    const allGreen = {
      ...FIXTURE_CHANGESET,
      approvals: FIXTURE_CHANGESET.approvals.map((a) => ({
        ...a,
        state: "approved" as const,
        rationale: undefined,
        reviewer: a.reviewer ?? "Latency Bot",
        decidedAt: a.decidedAt ?? "2025-02-21T11:36:00Z",
      })),
    };
    rerender(<ChangesetApprovals changeset={allGreen} onMerge={onMerge} />);
    const btn2 = screen.getByTestId(
      `changeset-merge-${FIXTURE_CHANGESET.id}`,
    ) as HTMLButtonElement;
    expect(btn2.disabled).toBe(false);
    fireEvent.click(btn2);
    expect(onMerge).toHaveBeenCalledWith(
      expect.objectContaining({ id: FIXTURE_CHANGESET.id }),
    );
  });

  it("surfaces validation errors when an axis is missing", () => {
    const broken = {
      ...FIXTURE_CHANGESET,
      approvals: FIXTURE_CHANGESET.approvals.filter((a) => a.axis !== "latency"),
    };
    render(<ChangesetApprovals changeset={broken} />);
    expect(
      screen.getByTestId(`changeset-validation-${broken.id}`).textContent,
    ).toContain("latency");
    expect(
      (screen.getByTestId(`changeset-merge-${broken.id}`) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
});

describe("PairDebugPanel", () => {
  it("renders presence, scrubber, and trace events with focused highlight", () => {
    render(<PairDebugPanel session={FIXTURE_PAIR_DEBUG} />);
    expect(screen.getByTestId("presence-bar")).toBeInTheDocument();
    expect(screen.getByTestId("playhead-readout").textContent).toContain(
      "1200ms",
    );
    // ev_3 @ 1180ms ≤ 1200ms → focused
    expect(screen.getByTestId("trace-event-ev_3").className).toContain(
      "border-sky-300",
    );
  });

  it("jumping via a row updates the playhead and fires onScrub", () => {
    const onScrub = vi.fn();
    render(<PairDebugPanel session={FIXTURE_PAIR_DEBUG} onScrub={onScrub} />);
    fireEvent.click(screen.getByTestId("trace-jump-ev_5"));
    expect(onScrub).toHaveBeenCalledWith(2600);
    expect(screen.getByTestId("playhead-readout").textContent).toContain(
      "2600ms",
    );
  });
});

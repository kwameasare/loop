import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import {
  FIXTURE_ACTION_DRIVE,
  FIXTURE_ACTION_SUGGEST,
  FIXTURE_OPERATOR,
  FIXTURE_REVIEW,
  FIXTURE_RUBBER_DUCK,
} from "@/lib/ai-cobuilder";

import { CoBuilderPanel } from "./co-builder-panel";
import { RubberDuck } from "./rubber-duck";
import { SecondPairOfEyes } from "./second-pair-of-eyes";

describe("CoBuilderPanel", () => {
  it("renders selection context, mode pill, diff, provenance, and apply button", () => {
    render(
      <CoBuilderPanel
        action={FIXTURE_ACTION_SUGGEST}
        operator={FIXTURE_OPERATOR}
        selectionContext="agents/refunds-bot/flow/escalate.ts:14"
      />,
    );
    expect(
      screen.getByTestId("cobuilder-selection-act_offer_callback"),
    ).toHaveTextContent("agents/refunds-bot/flow/escalate.ts:14");
    expect(
      screen.getByTestId("cobuilder-mode-act_offer_callback"),
    ).toHaveTextContent("Suggest");
    expect(
      screen.getByTestId("cobuilder-diff-act_offer_callback"),
    ).toHaveTextContent("offerCallback");
    expect(
      screen.getByTestId("cobuilder-provenance-act_offer_callback"),
    ).toHaveTextContent("comment thread th_refund_escalate");
    expect(
      screen.getByTestId("cobuilder-apply-act_offer_callback"),
    ).not.toBeDisabled();
  });

  it("blocks apply and shows reasons when consent fails", () => {
    render(
      <CoBuilderPanel
        action={FIXTURE_ACTION_DRIVE}
        operator={FIXTURE_OPERATOR}
        selectionContext="agents/refunds-bot/kb/index.json"
      />,
    );
    const blocked = screen.getByTestId("cobuilder-blocked-act_drive_kb_rebuild");
    expect(blocked).toHaveTextContent(/mode/);
    expect(blocked).toHaveTextContent(/scope/);
    expect(
      screen.getByTestId("cobuilder-apply-act_drive_kb_rebuild"),
    ).toBeDisabled();
  });

  it("invokes onApply when allowed action is applied", () => {
    const onApply = vi.fn();
    render(
      <CoBuilderPanel
        action={FIXTURE_ACTION_SUGGEST}
        operator={FIXTURE_OPERATOR}
        selectionContext="agents/refunds-bot/flow/escalate.ts:14"
        onApply={onApply}
      />,
    );
    fireEvent.click(
      screen.getByTestId("cobuilder-apply-act_offer_callback"),
    );
    expect(onApply).toHaveBeenCalledTimes(1);
    expect(onApply.mock.calls[0][0]).toBe("act_offer_callback");
    expect(
      screen.getByTestId("cobuilder-applied-act_offer_callback"),
    ).toBeInTheDocument();
  });
});

describe("RubberDuck", () => {
  it("renders failure summary, ordered findings, and proposed fix", () => {
    render(<RubberDuck diagnosis={FIXTURE_RUBBER_DUCK} />);
    expect(
      screen.getByTestId("rubber-duck-summary-rd_001"),
    ).toHaveTextContent("expected escalate");
    const list = screen.getByTestId("rubber-duck-steps-rd_001");
    expect(list.children).toHaveLength(3);
    expect(
      screen.getByTestId("rubber-duck-fix-rd_001"),
    ).toHaveTextContent("Pass refund-ceiling into policy reasoner");
  });
});

describe("SecondPairOfEyes", () => {
  it("renders all five bullets with severity and evidence", () => {
    render(<SecondPairOfEyes review={FIXTURE_REVIEW} />);
    for (const b of FIXTURE_REVIEW.bullets) {
      expect(
        screen.getByTestId(`second-pair-bullet-${b.id}`),
      ).toBeInTheDocument();
      expect(
        screen.getByTestId(`second-pair-evidence-${b.id}`),
      ).toHaveTextContent(b.evidenceRef);
    }
    expect(
      screen.getByTestId("second-pair-blocked-act_offer_callback"),
    ).toHaveTextContent("1 blocker");
  });

  it("surfaces a shape error when bullets are not exactly 5", () => {
    render(
      <SecondPairOfEyes
        review={{
          ...FIXTURE_REVIEW,
          bullets: FIXTURE_REVIEW.bullets.slice(0, 4),
        }}
      />,
    );
    expect(
      screen.getByTestId("second-pair-shape-error-act_offer_callback"),
    ).toHaveTextContent(/exactly 5/);
  });
});

import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import {
  FIXTURE_BOTPRESS_CUTOVER,
  FIXTURE_BOTPRESS_DIFFS,
  FIXTURE_BOTPRESS_LINEAGE,
  FIXTURE_BOTPRESS_READINESS,
  FIXTURE_BOTPRESS_REPAIRS,
  FIXTURE_BOTPRESS_REPLAY,
} from "@/lib/botpress-import";

import { CutoverPanel } from "./cutover-panel";
import { ParityHarness } from "./parity-harness";

describe("ParityHarness", () => {
  function setup(onAcceptRepair = vi.fn()) {
    render(
      <ParityHarness
        lineage={FIXTURE_BOTPRESS_LINEAGE}
        readiness={FIXTURE_BOTPRESS_READINESS}
        diffs={FIXTURE_BOTPRESS_DIFFS}
        replay={FIXTURE_BOTPRESS_REPLAY}
        repairs={FIXTURE_BOTPRESS_REPAIRS}
        onAcceptRepair={onAcceptRepair}
      />,
    );
    return { onAcceptRepair };
  }

  it("renders lineage, readiness, default structure pane", () => {
    setup();
    expect(screen.getByTestId("parity-harness")).toBeInTheDocument();
    expect(screen.getByTestId("lineage-step-parse")).toBeInTheDocument();
    expect(screen.getByTestId("lineage-step-secrets").textContent).toContain("warn");
    expect(screen.getByTestId("parity-readiness").textContent).toContain("78%");
    expect(screen.getByTestId("diff-row-diff_str_2").textContent).toContain("blocking");
  });

  it("switches to behavior, cost, risk diff modes", () => {
    setup();
    fireEvent.click(screen.getByTestId("parity-tab-behavior"));
    expect(screen.getByTestId("diff-row-diff_beh_2")).toBeInTheDocument();
    expect(screen.queryByTestId("diff-row-diff_str_2")).toBeNull();

    fireEvent.click(screen.getByTestId("parity-tab-cost"));
    expect(screen.getByTestId("diff-row-diff_cost_2").textContent).toContain("blocking");
    expect(screen.getByTestId("diff-row-diff_cost_2").textContent).toContain("+320ms");

    fireEvent.click(screen.getByTestId("parity-tab-risk"));
    expect(screen.getByTestId("diff-row-diff_risk_1")).toBeInTheDocument();
  });

  it("replay summary shows pass/regress/improve breakdown", () => {
    setup();
    const replay = screen.getByTestId("parity-replay");
    expect(replay.textContent).toContain("2 pass");
    expect(replay.textContent).toContain("1 regress");
    expect(replay.textContent).toContain("1 improve");
    expect(screen.getByTestId("replay-row-rp_003").textContent).toContain("regress");
  });

  it("accepting a repair fires the callback and shows accepted state", () => {
    const { onAcceptRepair } = setup();
    fireEvent.click(screen.getByTestId("repair-accept-rep_2"));
    expect(onAcceptRepair).toHaveBeenCalledTimes(1);
    expect(onAcceptRepair).toHaveBeenCalledWith(
      expect.objectContaining({ id: "rep_2" }),
    );
    expect(screen.getByTestId("repair-accepted-rep_2")).toBeInTheDocument();
  });
});

describe("CutoverPanel", () => {
  it("renders shadow summary, canary stages, rollback triggers", () => {
    render(<CutoverPanel plan={FIXTURE_BOTPRESS_CUTOVER} />);
    expect(screen.getByTestId("cutover-panel")).toBeInTheDocument();
    expect(screen.getByTestId("shadow-summary").textContent).toContain("96%");
    expect(screen.getByTestId("canary-stage-canary_10pct").textContent).toContain(
      "in_progress",
    );
    expect(screen.getByTestId("rollback-trigger-rb_regress")).toBeInTheDocument();
  });

  it("advance button only on the in-progress stage; advances via callback", () => {
    const onAdvance = vi.fn();
    render(<CutoverPanel plan={FIXTURE_BOTPRESS_CUTOVER} onAdvance={onAdvance} />);
    expect(screen.queryByTestId("canary-advance-canary_1pct")).toBeNull();
    expect(screen.queryByTestId("canary-advance-canary_50pct")).toBeNull();
    fireEvent.click(screen.getByTestId("canary-advance-canary_10pct"));
    expect(onAdvance).toHaveBeenCalledWith("canary_10pct");
  });

  it("manual rollback shows confirmation and disables further advances", () => {
    const onRollback = vi.fn();
    render(<CutoverPanel plan={FIXTURE_BOTPRESS_CUTOVER} onRollback={onRollback} />);
    fireEvent.click(screen.getByTestId("manual-rollback"));
    expect(onRollback).toHaveBeenCalledWith("manual");
    expect(screen.getByTestId("rollback-confirmation")).toBeInTheDocument();
    expect(screen.queryByTestId("canary-advance-canary_10pct")).toBeNull();
  });

  it("invalid plan surfaces a validation error", () => {
    render(
      <CutoverPanel
        plan={{ ...FIXTURE_BOTPRESS_CUTOVER, rollbackTriggers: [] }}
      />,
    );
    expect(screen.getByTestId("cutover-validation-error").textContent).toMatch(
      /rollback/,
    );
  });
});

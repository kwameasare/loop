import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QualityDashboard } from "@/components/quality/quality-dashboard";
import { ScreenChecklist } from "@/components/quality/screen-checklist";
import { SAMPLE_QUALITY_REPORTS, blankReview } from "@/lib/quality";

describe("QualityDashboard", () => {
  it("summarizes north-star meeting screens and per-category failures", () => {
    render(<QualityDashboard reports={SAMPLE_QUALITY_REPORTS} />);
    const summary = screen.getByTestId("quality-summary");
    expect(summary).toHaveTextContent("3");
    expect(summary).toHaveTextContent("2 / 3");
    const rollup = screen.getByTestId("quality-category-rollup");
    expect(within(rollup).getByTestId("quality-category-clarity")).toHaveTextContent("1");
    expect(within(rollup).getByTestId("quality-category-delight")).toHaveTextContent("0");
  });

  it("filters to failing-only screens", () => {
    render(<QualityDashboard reports={SAMPLE_QUALITY_REPORTS} />);
    fireEvent.click(screen.getByTestId("quality-filter-failing"));
    const list = screen.getByTestId("quality-screen-list");
    expect(within(list).getByTestId("quality-row-/migrate/[id]")).toBeInTheDocument();
    expect(within(list).queryByTestId("quality-row-/agents/[id]/workbench")).toBeNull();
  });

  it("renders empty state when no screens match", () => {
    render(<QualityDashboard reports={[]} />);
    expect(screen.getByTestId("quality-empty")).toHaveTextContent(/no screens/i);
  });

  it("invokes onSelect with the chosen report", () => {
    const onSelect = vi.fn();
    render(<QualityDashboard reports={SAMPLE_QUALITY_REPORTS} onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("quality-row-/traces/[id]"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0].screen).toBe("/traces/[id]");
  });
});

describe("ScreenChecklist", () => {
  it("starts blank reviews fully unchecked and toggles items", () => {
    const initial = blankReview("/agents", "ux-thor", "2026-05-06", "Workbench");
    render(<ScreenChecklist initial={initial} />);
    const score = screen.getByTestId("checklist-score");
    expect(score).toHaveTextContent("0 /");
    expect(score).toHaveTextContent(/below north-star/i);

    const item = screen.getByTestId("checklist-item-cl-job");
    fireEvent.click(within(item).getByRole("checkbox"));
    expect(screen.getByTestId("checklist-score")).toHaveTextContent("1 /");
  });

  it("surfaces evidence link when a category has failures", () => {
    const trace = SAMPLE_QUALITY_REPORTS.find((r) => r.screen.includes("traces"))!;
    render(<ScreenChecklist initial={trace} />);
    const ev = screen.getByTestId("checklist-evidence-precision");
    expect(ev).toHaveTextContent("§37.3");
    // categories that pass do not surface the evidence call-out
    expect(screen.queryByTestId("checklist-evidence-clarity")).toBeNull();
  });

  it("calls onChange after each toggle", () => {
    const initial = blankReview("/agents", "ux-thor", "2026-05-06");
    const onChange = vi.fn();
    render(<ScreenChecklist initial={initial} onChange={onChange} />);
    const item = screen.getByTestId("checklist-item-de-progress");
    fireEvent.click(within(item).getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(
      onChange.mock.calls[0]?.[0].results.find(
        (r: { category: string }) => r.category === "delight",
      )!.passed,
    ).toContain("de-progress");
  });
});

import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportWizard } from "./import-wizard";
import { MigrationEntry } from "./migration-entry";
import { MigrationScreen } from "./migration-screen";
import { SourceGrid } from "./source-grid";
import { ThreePaneReview } from "./three-pane-review";
import { MIGRATION_SOURCES, REVIEW_ITEMS } from "@/lib/migration";

describe("MigrationEntry", () => {
  it("renders import as the first-class entry choice", () => {
    render(<MigrationEntry />);
    const importChoice = screen.getByTestId("migration-entry-import");
    expect(importChoice).toHaveAttribute("data-first-class", "true");
    // Heading copy comes from canonical entry list.
    expect(
      within(importChoice).getByText(/Import from existing platform/i),
    ).toBeInTheDocument();
    expect(
      within(importChoice).getByTestId("migration-entry-cta-import"),
    ).toHaveAttribute("href", "/migrate#sources");
  });

  it("does not raise template, git, or blank to first-class", () => {
    render(<MigrationEntry />);
    for (const id of ["template", "git", "blank"]) {
      expect(
        screen.getByTestId(`migration-entry-${id}`).getAttribute(
          "data-first-class",
        ),
      ).toBe("false");
    }
  });
});

describe("SourceGrid", () => {
  it("labels Botpress as verified and exposes reference docs", () => {
    render(<SourceGrid />);
    expect(screen.getByTestId("source-status-botpress")).toHaveTextContent(
      /verified/i,
    );
    const card = screen.getByTestId("source-card-botpress");
    expect(within(card).getByText(/Reference docs/i)).toHaveAttribute(
      "href",
      expect.stringContaining("botpress.com"),
    );
  });

  it("disables Start import for aspirational sources to avoid over-promising", () => {
    render(<SourceGrid />);
    const aspirational = MIGRATION_SOURCES.find(
      (s) => s.status === "aspirational",
    );
    if (!aspirational) {
      throw new Error("expected at least one aspirational source in fixtures");
    }
    const button = screen.getByTestId(`source-select-${aspirational.id}`);
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/Request partnership/i);
  });

  it("filters by status when a chip is clicked", () => {
    render(<SourceGrid />);
    fireEvent.click(screen.getByTestId("source-filter-verified"));
    const list = screen.getByTestId("source-grid-list");
    // Only verified cards remain; planned and aspirational are filtered out.
    expect(within(list).getByTestId("source-card-botpress")).toBeInTheDocument();
    expect(
      within(list).queryByTestId("source-card-rasa"),
    ).not.toBeInTheDocument();
  });

  it("invokes onSelect when a non-aspirational source is chosen", () => {
    const onSelect = vi.fn();
    render(<SourceGrid onSelect={onSelect} />);
    fireEvent.click(screen.getByTestId("source-select-botpress"));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0]?.id).toBe("botpress");
  });
});

describe("ImportWizard", () => {
  it("starts on choose-source and disables Back", () => {
    render(<ImportWizard />);
    expect(
      screen.getByTestId("import-wizard-step-detail").textContent,
    ).toMatch(/Choose source/i);
    expect(screen.getByTestId("import-wizard-back")).toBeDisabled();
  });

  it("advances through the canonical nine steps and reaches cutover", () => {
    const onStepChange = vi.fn();
    render(<ImportWizard onStepChange={onStepChange} />);
    for (let i = 0; i < 8; i += 1) {
      fireEvent.click(screen.getByTestId("import-wizard-next"));
    }
    expect(onStepChange).toHaveBeenCalledTimes(8);
    expect(onStepChange.mock.calls.at(-1)?.[0]).toBe("stage-cutover");
    expect(screen.getByTestId("import-wizard-next")).toBeDisabled();
    expect(screen.getByTestId("import-wizard-next")).toHaveTextContent(
      /Cutover armed/i,
    );
  });
});

describe("ThreePaneReview", () => {
  it("renders source / needs-eyes / loop panes for each item", () => {
    render(<ThreePaneReview items={REVIEW_ITEMS.slice(0, 1)} />);
    const item = screen.getByTestId(`review-item-${REVIEW_ITEMS[0]!.id}`);
    expect(
      within(item).getByText(/Source · read-only/i),
    ).toBeInTheDocument();
    expect(within(item).getByText(/Needs your eyes/i)).toBeInTheDocument();
    expect(within(item).getByText(/Loop · editable/i)).toBeInTheDocument();
  });

  it("flags blocking decisions with the high risk halo", () => {
    const blocking = REVIEW_ITEMS.find((i) => i.severity === "blocking");
    if (!blocking) throw new Error("fixtures must include a blocking item");
    render(<ThreePaneReview items={[blocking]} />);
    const item = screen.getByTestId(`review-item-${blocking.id}`);
    expect(within(item).getByTestId("risk-halo")).toHaveAttribute(
      "data-risk",
      "high",
    );
    expect(within(item).getByTestId(`review-severity-${blocking.id}`))
      .toHaveTextContent(/Blocking/i);
  });

  it("surfaces evidence text rather than hiding it", () => {
    const withEvidence = REVIEW_ITEMS.find((i) => i.evidence);
    if (!withEvidence) throw new Error("fixtures must include an evidence row");
    render(<ThreePaneReview items={[withEvidence]} />);
    expect(
      screen.getByTestId(`review-evidence-${withEvidence.id}`).textContent,
    ).toContain(withEvidence.evidence);
  });
});

describe("MigrationScreen", () => {
  it("composes entry, sources, wizard, and three-pane review", () => {
    render(<MigrationScreen />);
    expect(screen.getByTestId("migration-screen")).toBeInTheDocument();
    expect(screen.getByTestId("migration-entry")).toBeInTheDocument();
    expect(screen.getByTestId("source-grid")).toBeInTheDocument();
    expect(screen.getByTestId("import-wizard")).toBeInTheDocument();
    expect(screen.getByTestId("three-pane-review")).toBeInTheDocument();
  });

  it("shows a degraded state panel when blocking decisions exist", () => {
    render(<MigrationScreen />);
    const panel = screen.getByTestId("state-panel");
    expect(panel).toHaveAttribute("data-state", "degraded");
    expect(panel.textContent).toMatch(/Promotion blocked/i);
  });
});

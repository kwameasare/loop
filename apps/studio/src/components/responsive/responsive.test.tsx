import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MobileActionDeck } from "@/components/responsive/mobile-action-deck";
import { ResponsiveSurface } from "@/components/responsive/responsive-surface";
import { SecondMonitor } from "@/components/responsive/second-monitor";
import { TabletReviewPane } from "@/components/responsive/tablet-review-pane";
import { ResponsiveModeSwitcher } from "@/components/shell/responsive-mode-switcher";

describe("MobileActionDeck", () => {
  it("renders the eight urgent actions and emits the chosen id", () => {
    const onAction = vi.fn();
    render(<MobileActionDeck onAction={onAction} />);
    expect(screen.getByTestId("mobile-action-list").children).toHaveLength(8);
    fireEvent.click(screen.getByTestId("mobile-action-rollback"));
    expect(onAction).toHaveBeenCalledWith("rollback");
  });

  it("never renders an edit-agent affordance as a button", () => {
    render(<MobileActionDeck />);
    const list = screen.getByTestId("mobile-action-list");
    const labels = list.querySelectorAll("button");
    for (const btn of Array.from(labels)) {
      expect(btn.textContent ?? "").not.toMatch(/edit/i);
    }
  });
});

describe("TabletReviewPane", () => {
  it("renders the five canonical tablet surfaces", () => {
    render(<TabletReviewPane />);
    expect(screen.getByTestId("tablet-surface-trace-summary")).toBeInTheDocument();
    expect(screen.getByTestId("tablet-surface-cost-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("tablet-surface-approvals")).toBeInTheDocument();
    expect(screen.getByTestId("tablet-surface-conversation-review")).toBeInTheDocument();
    expect(screen.getByTestId("tablet-surface-parity-report")).toBeInTheDocument();
  });
});

describe("SecondMonitor", () => {
  it("renders the canonical four panes", () => {
    render(<SecondMonitor />);
    expect(screen.getByTestId("second-monitor-timeline")).toBeInTheDocument();
    expect(screen.getByTestId("second-monitor-production-tail")).toBeInTheDocument();
    expect(screen.getByTestId("second-monitor-inbox")).toBeInTheDocument();
    expect(screen.getByTestId("second-monitor-deploy-health")).toBeInTheDocument();
  });

  it("renders custom content per pane when provided", () => {
    render(
      <SecondMonitor>
        {{ timeline: <span data-testid="custom-timeline">live</span> }}
      </SecondMonitor>,
    );
    expect(screen.getByTestId("custom-timeline")).toHaveTextContent("live");
  });
});

describe("ResponsiveSurface", () => {
  it("renders the mobile deck on mobile mode", () => {
    render(<ResponsiveSurface mode="mobile" />);
    expect(screen.getByTestId("responsive-surface-mobile")).toBeInTheDocument();
    expect(screen.getByTestId("mobile-action-deck")).toBeInTheDocument();
  });

  it("renders the five large-display surfaces in large-display mode", () => {
    render(<ResponsiveSurface mode="large-display" />);
    const surfaces = screen.getByTestId("large-display-surfaces");
    expect(surfaces.children).toHaveLength(5);
  });

  it("always includes the second monitor block", () => {
    render(<ResponsiveSurface mode="desktop" />);
    expect(screen.getByTestId("second-monitor")).toBeInTheDocument();
  });
});

describe("ResponsiveModeSwitcher", () => {
  it("emits the chosen mode and reflects active selection", () => {
    const onChange = vi.fn();
    render(<ResponsiveModeSwitcher current="mobile" onChange={onChange} />);
    expect(screen.getByTestId("responsive-mode-mobile")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    fireEvent.click(screen.getByTestId("responsive-mode-tablet"));
    expect(onChange).toHaveBeenCalledWith("tablet");
  });
});

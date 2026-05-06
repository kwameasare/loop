import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConciergeConsentPanel } from "@/components/onboarding/concierge-consent";
import { GuidedSpotlight } from "@/components/onboarding/guided-spotlight";
import { ThreeDoors } from "@/components/onboarding/three-doors";
import { TemplateGallery } from "@/components/templates/template-gallery";

describe("ThreeDoors", () => {
  it("renders exactly the three canonical doors", () => {
    render(<ThreeDoors />);
    const list = screen.getByTestId("three-doors-list");
    expect(within(list).getAllByRole("button")).toHaveLength(3);
    expect(screen.getByTestId("door-import")).toBeInTheDocument();
    expect(screen.getByTestId("door-template")).toBeInTheDocument();
    expect(screen.getByTestId("door-blank")).toBeInTheDocument();
  });

  it("emits the door id on choose", () => {
    const onChoose = vi.fn();
    render(<ThreeDoors onChoose={onChoose} />);
    fireEvent.click(screen.getByTestId("door-template"));
    expect(onChoose).toHaveBeenCalledWith("template");
  });
});

describe("TemplateGallery", () => {
  it("shows working-agent stats for each template", () => {
    render(<TemplateGallery />);
    const support = screen.getByTestId("template-tmpl_support_agent");
    expect(support).toHaveTextContent("KB");
    expect(support).toHaveTextContent("Tools");
    expect(support).toHaveTextContent("Evals");
    expect(support).toHaveTextContent("Convos");
    expect(support).toHaveTextContent("/mo");
  });

  it("invokes onPick with the chosen template", () => {
    const onPick = vi.fn();
    render(<TemplateGallery onPick={onPick} />);
    fireEvent.click(screen.getByTestId("template-tmpl_voice_receptionist"));
    expect(onPick).toHaveBeenCalledTimes(1);
    expect(onPick.mock.calls[0]?.[0].id).toBe("tmpl_voice_receptionist");
  });
});

describe("GuidedSpotlight", () => {
  it("walks through three hints and finishes", () => {
    const onDismiss = vi.fn();
    render(<GuidedSpotlight onDismiss={onDismiss} />);
    expect(screen.getByTestId("spotlight-step")).toHaveTextContent("Step 1 of 3");
    fireEvent.click(screen.getByTestId("spotlight-next"));
    expect(screen.getByTestId("spotlight-step")).toHaveTextContent("Step 2 of 3");
    fireEvent.click(screen.getByTestId("spotlight-next"));
    expect(screen.getByTestId("spotlight-step")).toHaveTextContent("Step 3 of 3");
    fireEvent.click(screen.getByTestId("spotlight-finish"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("guided-spotlight")).toBeNull();
  });

  it("supports forever-dismiss from any step", () => {
    const onDismiss = vi.fn();
    render(<GuidedSpotlight onDismiss={onDismiss} />);
    fireEvent.click(screen.getByTestId("spotlight-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });
});

describe("ConciergeConsentPanel", () => {
  it("blocks acceptance when no scope is selected", () => {
    const onAccept = vi.fn();
    render(
      <ConciergeConsentPanel
        reviewer="ux-thor"
        onAccept={onAccept}
        now={() => "2026-05-04T10:00:00Z"}
      />,
    );
    // Untick the only default scope.
    fireEvent.click(screen.getByTestId("concierge-scope-transcripts"));
    fireEvent.click(screen.getByTestId("concierge-accept"));
    expect(screen.getByTestId("concierge-error")).toHaveTextContent(/scope/i);
    expect(onAccept).not.toHaveBeenCalled();
  });

  it("renders findings with consent echo and supports revoke", () => {
    const onAccept = vi.fn();
    const onRevoke = vi.fn();
    render(
      <ConciergeConsentPanel
        reviewer="ux-thor"
        onAccept={onAccept}
        onRevoke={onRevoke}
        now={() => "2026-05-04T10:00:00Z"}
      />,
    );
    fireEvent.click(screen.getByTestId("concierge-scope-tool-calls"));
    fireEvent.click(screen.getByTestId("concierge-accept"));
    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("concierge-result")).toHaveTextContent(
      /transcripts, tool-calls/,
    );
    expect(screen.getByTestId("concierge-result")).toHaveTextContent("ux-thor");
    expect(screen.getByTestId("concierge-improvement")).toHaveTextContent(
      /safe first improvement/i,
    );
    fireEvent.click(screen.getByTestId("concierge-revoke"));
    expect(onRevoke).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("concierge-result")).toBeNull();
    // back to the consent form
    expect(screen.getByTestId("concierge-consent")).toBeInTheDocument();
  });
});

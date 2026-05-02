/**
 * S471: Tests for flow starter templates.
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { FLOW_TEMPLATES } from "@/lib/flow-templates";
import { FlowTemplatePicker } from "./flow-template-picker";
import { FlowEditor } from "./flow-editor";

// ---------------------------------------------------------------------------
// FLOW_TEMPLATES data
// ---------------------------------------------------------------------------

describe("FLOW_TEMPLATES data", () => {
  it("has exactly 3 templates", () => {
    expect(FLOW_TEMPLATES).toHaveLength(3);
  });

  it("has ids: faq, support-triage, lead-qual", () => {
    const ids = FLOW_TEMPLATES.map((t) => t.id);
    expect(ids).toContain("faq");
    expect(ids).toContain("support-triage");
    expect(ids).toContain("lead-qual");
  });

  it("each template starts with a start node and ends with an end node", () => {
    for (const tpl of FLOW_TEMPLATES) {
      expect(tpl.nodes.some((n) => n.type === "start")).toBe(true);
      expect(tpl.nodes.some((n) => n.type === "end")).toBe(true);
    }
  });

  it("each template has at least one edge", () => {
    for (const tpl of FLOW_TEMPLATES) {
      expect(tpl.edges.length).toBeGreaterThan(0);
    }
  });
});

// ---------------------------------------------------------------------------
// FlowTemplatePicker component tests
// ---------------------------------------------------------------------------

describe("FlowTemplatePicker", () => {
  it("renders all 3 template cards", () => {
    render(<FlowTemplatePicker onSelect={() => {}} onDismiss={() => {}} />);
    expect(screen.getByTestId("flow-template-card-faq")).toBeInTheDocument();
    expect(screen.getByTestId("flow-template-card-support-triage")).toBeInTheDocument();
    expect(screen.getByTestId("flow-template-card-lead-qual")).toBeInTheDocument();
  });

  it("apply button is disabled when nothing is selected", () => {
    render(<FlowTemplatePicker onSelect={() => {}} onDismiss={() => {}} />);
    expect(screen.getByTestId("flow-template-apply")).toBeDisabled();
  });

  it("apply button enables after selecting a card", () => {
    render(<FlowTemplatePicker onSelect={() => {}} onDismiss={() => {}} />);
    fireEvent.click(screen.getByTestId("flow-template-card-faq"));
    expect(screen.getByTestId("flow-template-apply")).not.toBeDisabled();
  });

  it("calls onSelect with correct template when apply clicked", () => {
    const onSelect = vi.fn();
    render(<FlowTemplatePicker onSelect={onSelect} onDismiss={() => {}} />);
    fireEvent.click(screen.getByTestId("flow-template-card-support-triage"));
    fireEvent.click(screen.getByTestId("flow-template-apply"));
    expect(onSelect).toHaveBeenCalledOnce();
    expect(onSelect.mock.calls[0][0].id).toBe("support-triage");
  });

  it("calls onDismiss when cancel is clicked", () => {
    const onDismiss = vi.fn();
    render(<FlowTemplatePicker onSelect={() => {}} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByTestId("flow-template-cancel"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("calls onDismiss when close (✕) button clicked", () => {
    const onDismiss = vi.fn();
    render(<FlowTemplatePicker onSelect={() => {}} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByTestId("flow-template-close"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// FlowEditor — Templates toolbar button
// ---------------------------------------------------------------------------

describe("FlowEditor Templates button", () => {
  it("renders a Templates button in the toolbar", () => {
    render(<FlowEditor agentId="a1" />);
    expect(screen.getByTestId("flow-templates")).toBeInTheDocument();
  });

  it("opens template picker when Templates button is clicked", () => {
    render(<FlowEditor agentId="a1" />);
    expect(screen.queryByTestId("flow-template-picker")).toBeNull();
    fireEvent.click(screen.getByTestId("flow-templates"));
    expect(screen.getByTestId("flow-template-picker")).toBeInTheDocument();
  });

  it("applies template nodes to canvas and closes picker", () => {
    render(<FlowEditor agentId="a1" />);
    fireEvent.click(screen.getByTestId("flow-templates"));
    fireEvent.click(screen.getByTestId("flow-template-card-faq"));
    fireEvent.click(screen.getByTestId("flow-template-apply"));
    // Picker closed
    expect(screen.queryByTestId("flow-template-picker")).toBeNull();
    // FAQ template has 4 nodes
    const faqTpl = FLOW_TEMPLATES.find((t) => t.id === "faq")!;
    for (const node of faqTpl.nodes) {
      expect(screen.getByTestId(`flow-node-${node.id}`)).toBeInTheDocument();
    }
  });
});

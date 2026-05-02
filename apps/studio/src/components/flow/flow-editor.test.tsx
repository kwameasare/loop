import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { FLOW_NODE_KINDS, _resetFlowNodeIds } from "@/lib/flow-nodes";

import { FlowEditor } from "./flow-editor";
import { NodePalette } from "./node-palette";

beforeEach(() => {
  _resetFlowNodeIds();
});

describe("NodePalette", () => {
  it("renders one draggable button per node kind with a distinct icon", () => {
    render(<NodePalette />);
    for (const kind of FLOW_NODE_KINDS) {
      const item = screen.getByTestId(`palette-item-${kind.type}`);
      expect(item).toBeInTheDocument();
      expect(item.getAttribute("draggable")).toBe("true");
      expect(
        screen.getByTestId(`palette-icon-${kind.type}`).textContent,
      ).toBe(kind.icon);
    }
  });

  it("notifies callers when a drag starts", () => {
    const seen: string[] = [];
    render(<NodePalette onDragStart={(t) => seen.push(t)} />);
    fireEvent.dragStart(screen.getByTestId("palette-item-message"));
    expect(seen).toEqual(["message"]);
  });
});

describe("FlowEditor drag-and-drop", () => {
  it("creates a node on drop with the dragged type", async () => {
    render(<FlowEditor agentId="a1" pendingDragType="ai-task" />);
    const viewport = screen.getByTestId("flow-viewport");
    await act(async () => {
      fireEvent.drop(viewport, { clientX: 200, clientY: 150 });
    });
    const node = screen.getByTestId("flow-node-ai-task-1");
    expect(node).toBeInTheDocument();
    expect(node.getAttribute("data-node-type")).toBe("ai-task");
    // Placeholder hides once a node is present.
    expect(screen.queryByTestId("flow-placeholder")).toBeNull();
  });

  it("allows dropping multiple distinct node types", async () => {
    render(<FlowEditor agentId="a1" pendingDragType="start" />);
    const viewport = screen.getByTestId("flow-viewport");
    await act(async () => {
      fireEvent.drop(viewport, { clientX: 50, clientY: 50 });
    });
    expect(screen.getByTestId("flow-node-start-1")).toBeInTheDocument();
    // Switch the pending drag type via palette drag, then drop again.
    fireEvent.dragStart(screen.getByTestId("palette-item-end"));
    await act(async () => {
      fireEvent.drop(viewport, { clientX: 300, clientY: 200 });
    });
    expect(screen.getByTestId("flow-node-end-2")).toBeInTheDocument();
  });

  it("ignores drops when no drag type is pending", async () => {
    render(<FlowEditor agentId="a1" />);
    const viewport = screen.getByTestId("flow-viewport");
    await act(async () => {
      fireEvent.drop(viewport, { clientX: 100, clientY: 100 });
    });
    expect(screen.getByTestId("flow-placeholder")).toBeInTheDocument();
  });

  it("renders all known node kinds in the palette", () => {
    render(<FlowEditor agentId="a1" />);
    for (const kind of FLOW_NODE_KINDS) {
      expect(
        screen.getByTestId(`palette-item-${kind.type}`),
      ).toBeInTheDocument();
    }
  });
});

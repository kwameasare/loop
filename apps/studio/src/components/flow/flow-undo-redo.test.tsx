/**
 * S469: Tests for flow undo/redo (useFlowHistory hook + FlowEditor toolbar buttons).
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { renderHook, act } from "@testing-library/react";

import { useFlowHistory, HISTORY_CAP } from "@/lib/use-flow-history";
import { FlowEditor } from "./flow-editor";
import { type FlowNode } from "@/lib/flow-nodes";
import { type FlowEdge } from "@/lib/flow-edges";

// ---------------------------------------------------------------------------
// useFlowHistory unit tests
// ---------------------------------------------------------------------------

describe("useFlowHistory", () => {
  const n1: FlowNode = { id: "start-1", type: "start", x: 0, y: 0 };
  const n2: FlowNode = { id: "end-1", type: "end", x: 100, y: 0 };

  it("starts with initial state and canUndo=false canRedo=false", () => {
    const { result } = renderHook(() => useFlowHistory([n1], []));
    expect(result.current.nodes).toEqual([n1]);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });

  it("canUndo becomes true after push", () => {
    const { result } = renderHook(() => useFlowHistory([n1], []));
    act(() => {
      result.current.push();
      result.current.setNodes([n1, n2]);
    });
    expect(result.current.canUndo).toBe(true);
    expect(result.current.nodes).toHaveLength(2);
  });

  it("undo restores previous state", () => {
    const { result } = renderHook(() => useFlowHistory([n1], []));
    act(() => {
      result.current.push();
      result.current.setNodes([n1, n2]);
    });
    act(() => {
      result.current.undo();
    });
    expect(result.current.nodes).toEqual([n1]);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it("redo re-applies undone change", () => {
    const { result } = renderHook(() => useFlowHistory([n1], []));
    act(() => {
      result.current.push();
      result.current.setNodes([n1, n2]);
    });
    act(() => { result.current.undo(); });
    act(() => { result.current.redo(); });
    expect(result.current.nodes).toHaveLength(2);
    expect(result.current.canRedo).toBe(false);
  });

  it("new push clears redo stack", () => {
    const { result } = renderHook(() => useFlowHistory([n1], []));
    act(() => {
      result.current.push();
      result.current.setNodes([n1, n2]);
    });
    act(() => { result.current.undo(); });
    act(() => {
      result.current.push();
      result.current.setNodes([n1]);
    });
    expect(result.current.canRedo).toBe(false);
  });

  it("caps history at HISTORY_CAP entries", () => {
    const { result } = renderHook(() => useFlowHistory([], []));
    // Push HISTORY_CAP + 10 times; cap should keep only HISTORY_CAP snapshots
    act(() => {
      for (let i = 0; i < HISTORY_CAP + 10; i++) {
        result.current.push();
        result.current.setNodes([{ id: `start-${i}`, type: "start", x: i, y: 0 }]);
      }
    });
    // After all pushes canUndo must be true; and undo count should equal HISTORY_CAP
    expect(result.current.canUndo).toBe(true);
    // Drain the undo stack entirely
    let count = 0;
    while (result.current.canUndo) {
      act(() => { result.current.undo(); });
      count++;
      if (count > HISTORY_CAP + 20) break;
    }
    expect(count).toBe(HISTORY_CAP);
  });

  it("undo/redo also tracks edges", () => {
    const e1: FlowEdge = { id: "e_start-1_end-1", source: "start-1", target: "end-1" };
    const { result } = renderHook(() => useFlowHistory([n1, n2], []));
    act(() => {
      result.current.push();
      result.current.setEdges([e1]);
    });
    expect(result.current.edges).toHaveLength(1);
    act(() => { result.current.undo(); });
    expect(result.current.edges).toHaveLength(0);
    act(() => { result.current.redo(); });
    expect(result.current.edges).toHaveLength(1);
  });
});

// ---------------------------------------------------------------------------
// FlowEditor toolbar undo/redo button tests
// ---------------------------------------------------------------------------

describe("FlowEditor undo/redo toolbar", () => {
  it("renders undo and redo buttons (disabled initially)", () => {
    render(<FlowEditor agentId="a1" />);
    expect(screen.getByTestId("flow-undo")).toBeDisabled();
    expect(screen.getByTestId("flow-redo")).toBeDisabled();
  });

  it("undo button enables after a drop, and clicking restores empty state", () => {
    render(
      <FlowEditor
        agentId="a1"
        pendingDragType="message"
      />,
    );
    // Drop a node
    fireEvent.drop(screen.getByTestId("flow-viewport"), {
      clientX: 200,
      clientY: 200,
      dataTransfer: { getData: () => "" },
    });
    expect(screen.getByTestId("flow-undo")).not.toBeDisabled();

    // Click undo
    fireEvent.click(screen.getByTestId("flow-undo"));
    // Node should be gone
    expect(screen.queryByTestId(/^flow-node-/)).toBeNull();
    // Redo should now be enabled
    expect(screen.getByTestId("flow-redo")).not.toBeDisabled();
  });

  it("redo button works after undo", () => {
    render(
      <FlowEditor
        agentId="a1"
        pendingDragType="start"
      />,
    );
    fireEvent.drop(screen.getByTestId("flow-viewport"), {
      clientX: 100,
      clientY: 100,
      dataTransfer: { getData: () => "" },
    });
    fireEvent.click(screen.getByTestId("flow-undo"));
    expect(screen.queryByTestId(/^flow-node-/)).toBeNull();

    fireEvent.click(screen.getByTestId("flow-redo"));
    expect(screen.getByTestId(/^flow-node-/)).toBeInTheDocument();
  });
});

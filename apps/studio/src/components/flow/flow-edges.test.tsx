import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { _resetFlowEdgeIds } from "@/lib/flow-edges";
import { _resetFlowNodeIds } from "@/lib/flow-nodes";

import { FlowEditor } from "./flow-editor";

beforeEach(() => {
  _resetFlowNodeIds();
  _resetFlowEdgeIds();
});

const NODES = [
  { id: "start-1", type: "start" as const, x: 100, y: 100 },
  { id: "message-1", type: "message" as const, x: 300, y: 200 },
];

describe("Flow edge editing", () => {
  it("renders no edge layer when there are no edges", () => {
    render(<FlowEditor agentId="a1" initialNodes={NODES} />);
    expect(screen.queryByTestId("flow-edges")).toBeNull();
  });

  it("connects two nodes by mousedown on handle then click on target", async () => {
    render(<FlowEditor agentId="a1" initialNodes={NODES} />);
    await act(async () => {
      fireEvent.mouseDown(screen.getByTestId("flow-handle-start-1"));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-message-1"));
    });
    expect(screen.getByTestId("flow-edges")).toBeInTheDocument();
    expect(screen.getByTestId("flow-edge-edge-1")).toBeInTheDocument();
  });

  it("connects via the seam pendingConnectFromId for parity with the e2e flow", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={NODES}
        pendingConnectFromId="start-1"
      />,
    );
    await act(async () => {
      fireEvent.mouseUp(screen.getByTestId("flow-node-message-1"));
    });
    expect(screen.getByTestId("flow-edge-edge-1")).toBeInTheDocument();
  });

  it("does not connect a node to itself", async () => {
    render(
      <FlowEditor
        agentId="a1"
        initialNodes={NODES}
        pendingConnectFromId="start-1"
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-node-start-1"));
    });
    expect(screen.queryByTestId("flow-edges")).toBeNull();
  });

  it("clicking an edge prompts for confirmation and deletes on accept", async () => {
    let asked: { source: string; target: string } | null = null;
    render(
      <FlowEditor
        agentId="a1"
        confirmDelete={(edge) => {
          asked = { source: edge.source, target: edge.target };
          return true;
        }}
        initialEdges={[{ id: "edge-1", source: "start-1", target: "message-1" }]}
        initialNodes={NODES}
      />,
    );
    expect(screen.getByTestId("flow-edge-edge-1")).toBeInTheDocument();
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-edge-edge-1"));
    });
    expect(asked).toEqual({ source: "start-1", target: "message-1" });
    expect(screen.queryByTestId("flow-edge-edge-1")).toBeNull();
  });

  it("declined confirmation keeps the edge in place", async () => {
    render(
      <FlowEditor
        agentId="a1"
        confirmDelete={() => false}
        initialEdges={[{ id: "edge-1", source: "start-1", target: "message-1" }]}
        initialNodes={NODES}
      />,
    );
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-edge-edge-1"));
    });
    expect(screen.getByTestId("flow-edge-edge-1")).toBeInTheDocument();
  });
});

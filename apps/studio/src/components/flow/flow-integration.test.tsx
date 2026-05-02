/**
 * Integration test for S472 — build a graph, save it, run it, assert the
 * conditional branch fires.
 *
 * Wires together the real ``FlowPersistencePanel``, the real
 * ``FlowEmulatorPanel``, and a fixture transport backed by ``runFlow``.
 * The transport reads the latest YAML the persistence layer stored for
 * the agent, parses it back to a ``FlowDoc`` via ``flowFromYaml``, and
 * walks the graph using a decider that picks a branch based on the
 * user's input text. The test asserts that the conditional node routes
 * to branch_a for one input and branch_b for the other — i.e. the AC.
 */
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { useCallback, useState } from "react";
import { describe, expect, it } from "vitest";

import { FlowEmulatorPanel } from "@/components/flow/flow-emulator-panel";
import { FlowPersistencePanel } from "@/components/flow/flow-persistence-panel";
import type { FlowEdge } from "@/lib/flow-edges";
import type { FlowNode } from "@/lib/flow-nodes";
import { runFlow, runResultToEvents } from "@/lib/flow-runner";
import type { TurnEvent } from "@/lib/sdk-types";
import {
  type FlowApi,
  flowFromYaml,
  flowToYaml,
  makeMemoryFlowApi,
} from "@/lib/flow-yaml";
import type { EmulatorTransport } from "@/lib/emulator-transport";

const SEED_NODES: FlowNode[] = [
  { id: "start-1", type: "start", x: 0, y: 0 },
  { id: "condition-1", type: "condition", x: 100, y: 0 },
  { id: "branch_a", type: "message", x: 200, y: -50 },
  { id: "branch_b", type: "message", x: 200, y: 50 },
  { id: "end-a", type: "end", x: 300, y: -50 },
  { id: "end-b", type: "end", x: 300, y: 50 },
];

const SEED_EDGES: FlowEdge[] = [
  { id: "e1", source: "start-1", target: "condition-1" },
  { id: "e2", source: "condition-1", target: "branch_a" },
  { id: "e3", source: "condition-1", target: "branch_b" },
  { id: "e4", source: "branch_a", target: "end-a" },
  { id: "e5", source: "branch_b", target: "end-b" },
];

/**
 * Builds an emulator transport that, on each ``start()`` call, reads the
 * agent's currently-persisted YAML, walks the graph, and emits the run
 * as an SSE-style event stream.
 */
function makeRunnerTransport(api: FlowApi, agentId: string): EmulatorTransport {
  return {
    async *start({ text }) {
      const v = await api.load(agentId);
      if (!v) return;
      const doc = flowFromYaml(v.flowYaml);
      const result = runFlow(doc, "start-1", (_node, outgoing) => {
        // Decider: any input containing "buy" picks branch_a, else branch_b.
        const wantsBuy = /buy/i.test(text);
        const targetId = wantsBuy ? "branch_a" : "branch_b";
        const edge = outgoing.find((e) => e.target === targetId);
        return edge ? edge.target : null;
      });
      for (const evt of runResultToEvents(result)) {
        yield evt;
      }
    },
  };
}

interface HarnessProps {
  api: FlowApi;
  agentId: string;
  onTurnEvent: (e: TurnEvent) => void;
}

function Harness(props: HarnessProps) {
  const [doc, setDoc] = useState<{ nodes: FlowNode[]; edges: FlowEdge[] }>({
    nodes: SEED_NODES,
    edges: SEED_EDGES,
  });
  const onLoad = useCallback(
    (next: { nodes: FlowNode[]; edges: FlowEdge[] }) => setDoc(next),
    [],
  );
  return (
    <div>
      <FlowPersistencePanel
        agentId={props.agentId}
        api={props.api}
        doc={doc}
        onLoad={onLoad}
      />
      <FlowEmulatorPanel
        agentId={props.agentId}
        onTurnEvent={props.onTurnEvent}
        transport={makeRunnerTransport(props.api, props.agentId)}
      />
    </div>
  );
}

function nodeIdsFromEvents(events: TurnEvent[]): string[] {
  return events
    .filter((e) => e.type === "trace")
    .map((e) => (e.payload as { node_entered?: string }).node_entered ?? "");
}

describe("S472 flow integration — build → save → run → branch hit", () => {
  it("conditional node routes to branch_a for matching input", async () => {
    const api = makeMemoryFlowApi({ agentId: "agt_x" });
    const seen: TurnEvent[] = [];
    render(
      <Harness
        agentId="agt_x"
        api={api}
        onTurnEvent={(e) => seen.push(e)}
      />,
    );

    // Wait for initial load to settle (no seeded yaml → idle).
    await waitFor(() => {
      expect(screen.getByTestId("flow-persistence")).toBeInTheDocument();
    });

    // Save the in-memory graph to the api.
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("flow-saved")).toBeInTheDocument();
    });

    // Confirm the persisted YAML round-trips to the same structure.
    const persisted = await api.load("agt_x");
    expect(persisted).not.toBeNull();
    expect(flowFromYaml(persisted!.flowYaml)).toEqual({
      nodes: SEED_NODES,
      edges: SEED_EDGES,
    });
    expect(persisted!.flowYaml).toBe(
      flowToYaml({ nodes: SEED_NODES, edges: SEED_EDGES }),
    );

    // Run the graph with input that should hit branch_a.
    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "buy now" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("emulator-status").textContent).toBe("idle");
    });

    const path = nodeIdsFromEvents(seen);
    expect(path).toContain("condition-1");
    expect(path).toContain("branch_a");
    expect(path).not.toContain("branch_b");
    expect(path[path.length - 1]).toBe("end-a");
  });

  it("the same saved graph routes to branch_b for non-matching input", async () => {
    const api = makeMemoryFlowApi({ agentId: "agt_y" });
    const seen: TurnEvent[] = [];
    render(
      <Harness
        agentId="agt_y"
        api={api}
        onTurnEvent={(e) => seen.push(e)}
      />,
    );
    await waitFor(() => {
      expect(screen.getByTestId("flow-persistence")).toBeInTheDocument();
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("flow-save"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("flow-saved")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("emulator-input"), {
      target: { value: "just looking" },
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId("emulator-play"));
    });
    await waitFor(() => {
      expect(screen.getByTestId("emulator-status").textContent).toBe("idle");
    });

    const path = nodeIdsFromEvents(seen);
    expect(path).toContain("branch_b");
    expect(path).not.toContain("branch_a");
    expect(path[path.length - 1]).toBe("end-b");
  });
});

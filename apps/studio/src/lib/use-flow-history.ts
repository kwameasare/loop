/**
 * S469: Undo/redo hook for flow nodes+edges, capped at HISTORY_CAP entries.
 */
import { useCallback, useRef, useState } from "react";
import { type FlowEdge } from "@/lib/flow-edges";
import { type FlowNode } from "@/lib/flow-nodes";

export const HISTORY_CAP = 50;

export interface FlowSnapshot {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

export interface UseFlowHistoryReturn {
  nodes: FlowNode[];
  edges: FlowEdge[];
  setNodes: (nodes: FlowNode[]) => void;
  setEdges: (edges: FlowEdge[]) => void;
  /** Push the current nodes+edges as a snapshot before a mutation. */
  push: () => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

export function useFlowHistory(
  initialNodes: FlowNode[],
  initialEdges: FlowEdge[],
): UseFlowHistoryReturn {
  const [nodes, setNodesRaw] = useState<FlowNode[]>(initialNodes);
  const [edges, setEdgesRaw] = useState<FlowEdge[]>(initialEdges);
  // past[0] = oldest, past[past.length - 1] = most recent undo target
  const pastRef = useRef<FlowSnapshot[]>([]);
  const futureRef = useRef<FlowSnapshot[]>([]);
  // We store current in a ref so callbacks can capture it without stale closure.
  const currentRef = useRef<FlowSnapshot>({ nodes: initialNodes, edges: initialEdges });
  const [historyVersion, setHistoryVersion] = useState(0);

  function bump() {
    setHistoryVersion((v) => v + 1);
  }

  const setNodes = useCallback((next: FlowNode[]) => {
    currentRef.current = { ...currentRef.current, nodes: next };
    setNodesRaw(next);
  }, []);

  const setEdges = useCallback((next: FlowEdge[]) => {
    currentRef.current = { ...currentRef.current, edges: next };
    setEdgesRaw(next);
  }, []);

  /**
   * Call BEFORE mutating nodes/edges. Saves current state to past stack and
   * clears the redo stack.
   */
  const push = useCallback(() => {
    const snap = { ...currentRef.current };
    pastRef.current = [...pastRef.current.slice(-(HISTORY_CAP - 1)), snap];
    futureRef.current = [];
    bump();
  }, []);

  const undo = useCallback(() => {
    if (pastRef.current.length === 0) return;
    const target = pastRef.current[pastRef.current.length - 1];
    futureRef.current = [{ ...currentRef.current }, ...futureRef.current];
    pastRef.current = pastRef.current.slice(0, -1);
    currentRef.current = { ...target };
    setNodesRaw(target.nodes);
    setEdgesRaw(target.edges);
    bump();
  }, []);

  const redo = useCallback(() => {
    if (futureRef.current.length === 0) return;
    const target = futureRef.current[0];
    pastRef.current = [...pastRef.current, { ...currentRef.current }];
    futureRef.current = futureRef.current.slice(1);
    currentRef.current = { ...target };
    setNodesRaw(target.nodes);
    setEdgesRaw(target.edges);
    bump();
  }, []);

  // Use historyVersion only to force re-render for canUndo/canRedo reactivity.
  void historyVersion;

  return {
    nodes,
    edges,
    setNodes,
    setEdges,
    push,
    undo,
    redo,
    canUndo: pastRef.current.length > 0,
    canRedo: futureRef.current.length > 0,
  };
}

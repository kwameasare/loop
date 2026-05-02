import type { FlowEdge } from "./flow-edges";
import type { FlowNode } from "./flow-nodes";
import type { FlowDoc } from "./flow-yaml";
import type { TurnEvent } from "./sdk-types";

/**
 * Decision callback supplied by the caller (typically the runtime, or a
 * fixture in tests). Receives a node that has more than one outgoing
 * edge and must return the id of the chosen next node, or ``null`` to
 * halt the walk.
 *
 * For nodes with zero or one outgoing edges, the walker handles routing
 * automatically and the decider is not consulted.
 */
export type FlowDecider = (
  node: FlowNode,
  outgoing: FlowEdge[],
) => string | null;

export interface FlowRunResult {
  /** Ordered list of visited node ids. */
  visited: string[];
  /** Reason the walk terminated. */
  reason: "complete" | "no-outgoing" | "decider-stop" | "max-steps" | "missing-node";
}

/**
 * Walks the {@link FlowDoc} starting at ``startId``. Returns the visit
 * sequence and the termination reason. The walker is pure: it never
 * mutates the doc.
 */
export function runFlow(
  doc: FlowDoc,
  startId: string,
  decide: FlowDecider,
  maxSteps = 100,
): FlowRunResult {
  const byId = new Map(doc.nodes.map((n) => [n.id, n]));
  const visited: string[] = [];
  let cursor: string | null = startId;
  for (let i = 0; i < maxSteps; i += 1) {
    if (!cursor) return { visited, reason: "decider-stop" };
    const node = byId.get(cursor);
    if (!node) return { visited, reason: "missing-node" };
    visited.push(node.id);
    const outgoing = doc.edges.filter((e) => e.source === node.id);
    if (outgoing.length === 0) return { visited, reason: "complete" };
    if (outgoing.length === 1) {
      cursor = outgoing[0].target;
      continue;
    }
    const next = decide(node, outgoing);
    if (next === null) return { visited, reason: "decider-stop" };
    cursor = next;
  }
  return { visited, reason: "max-steps" };
}

/**
 * Translates a {@link FlowRunResult} into the {@link TurnEvent} stream
 * that the emulator panel (and inspector) consume. Each visited node id
 * becomes a ``trace`` event, and a final ``complete`` event terminates
 * the stream when the run finished cleanly.
 */
export function runResultToEvents(
  result: FlowRunResult,
  ts = "2025-01-01T00:00:00Z",
): TurnEvent[] {
  const events: TurnEvent[] = result.visited.map((id) => ({
    type: "trace",
    payload: { node_entered: id },
    ts,
  }));
  if (result.reason === "complete") {
    events.push({ type: "complete", payload: {}, ts });
  } else {
    events.push({
      type: "degrade",
      payload: { reason: result.reason },
      ts,
    });
  }
  return events;
}

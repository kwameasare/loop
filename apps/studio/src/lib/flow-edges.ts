export interface FlowEdge {
  id: string;
  source: string;
  target: string;
}

let counter = 0;

export function nextFlowEdgeId(): string {
  counter += 1;
  return `edge-${counter}`;
}

export function _resetFlowEdgeIds(): void {
  counter = 0;
}

export function canConnect(
  edges: FlowEdge[],
  source: string,
  target: string,
): boolean {
  if (!source || !target) return false;
  if (source === target) return false;
  return !edges.some((e) => e.source === source && e.target === target);
}

export function addEdge(
  edges: FlowEdge[],
  source: string,
  target: string,
): FlowEdge[] {
  if (!canConnect(edges, source, target)) return edges;
  return [...edges, { id: nextFlowEdgeId(), source, target }];
}

export function removeEdge(edges: FlowEdge[], id: string): FlowEdge[] {
  return edges.filter((e) => e.id !== id);
}

export function edgesTouching(edges: FlowEdge[], nodeId: string): FlowEdge[] {
  return edges.filter((e) => e.source === nodeId || e.target === nodeId);
}

export function pruneEdgesForRemovedNode(
  edges: FlowEdge[],
  nodeId: string,
): FlowEdge[] {
  return edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
}

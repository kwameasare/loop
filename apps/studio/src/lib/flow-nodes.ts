/**
 * Flow node types and palette metadata. Kept in lib so it can be imported
 * by both the canvas and the palette without circular module ties.
 */

export type FlowNodeType =
  | "start"
  | "message"
  | "condition"
  | "ai-task"
  | "http"
  | "code"
  | "end";

export interface FlowNode {
  id: string;
  type: FlowNodeType;
  /** World-space position in pixels. */
  x: number;
  y: number;
}

export interface FlowNodeKind {
  type: FlowNodeType;
  label: string;
  description: string;
  /** Single-character glyph used as a stand-in for an icon. */
  icon: string;
  color: string;
}

export const FLOW_NODE_KINDS: FlowNodeKind[] = [
  {
    type: "start",
    label: "Start",
    description: "Entry point of the flow.",
    icon: "▶",
    color: "bg-emerald-100 text-emerald-700",
  },
  {
    type: "message",
    label: "Message",
    description: "Send a static message to the user.",
    icon: "✉",
    color: "bg-sky-100 text-sky-700",
  },
  {
    type: "condition",
    label: "Condition",
    description: "Branch based on a boolean expression.",
    icon: "◇",
    color: "bg-amber-100 text-amber-700",
  },
  {
    type: "ai-task",
    label: "AI task",
    description: "Run an LLM call with a prompt template.",
    icon: "✦",
    color: "bg-violet-100 text-violet-700",
  },
  {
    type: "http",
    label: "HTTP",
    description: "Call an external HTTP endpoint.",
    icon: "⇄",
    color: "bg-blue-100 text-blue-700",
  },
  {
    type: "code",
    label: "Code",
    description: "Run a custom code block.",
    icon: "{}",
    color: "bg-zinc-200 text-zinc-700",
  },
  {
    type: "end",
    label: "End",
    description: "Terminate the flow.",
    icon: "■",
    color: "bg-red-100 text-red-700",
  },
];

export function getNodeKind(type: FlowNodeType): FlowNodeKind {
  const kind = FLOW_NODE_KINDS.find((k) => k.type === type);
  if (!kind) throw new Error(`unknown flow node type: ${type}`);
  return kind;
}

export const FLOW_DRAG_MIME = "application/x-loop-flow-node";

let nodeCounter = 0;
/** Reset the in-memory id counter; intended for tests only. */
export function _resetFlowNodeIds() {
  nodeCounter = 0;
}
export function nextFlowNodeId(type: FlowNodeType): string {
  nodeCounter += 1;
  return `${type}-${nodeCounter}`;
}

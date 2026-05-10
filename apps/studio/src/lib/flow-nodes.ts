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
    color: "bg-success/10 text-success",
  },
  {
    type: "message",
    label: "Message",
    description: "Send a static message to the user.",
    icon: "✉",
    color: "bg-info/10 text-info",
  },
  {
    type: "condition",
    label: "Condition",
    description: "Branch based on a boolean expression.",
    icon: "◇",
    color: "bg-warning/10 text-warning",
  },
  {
    type: "ai-task",
    label: "AI task",
    description: "Run an LLM call with a prompt template.",
    icon: "✦",
    color: "bg-primary/10 text-primary",
  },
  {
    type: "http",
    label: "HTTP",
    description: "Call an external HTTP endpoint.",
    icon: "⇄",
    color: "bg-accent text-accent-foreground",
  },
  {
    type: "code",
    label: "Code",
    description: "Run a custom code block.",
    icon: "{}",
    color: "bg-muted text-muted-foreground",
  },
  {
    type: "end",
    label: "End",
    description: "Terminate the flow.",
    icon: "■",
    color: "bg-destructive/10 text-destructive",
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

export type FlowVariableValue =
  | string
  | number
  | boolean
  | null
  | FlowVariableValue[]
  | { [key: string]: FlowVariableValue };

export interface FlowFrame {
  /**
   * Identifier of the flow node whose execution produced this frame.
   */
  nodeId: string;
  /**
   * Wall-clock timestamp (ms since epoch) when the frame was captured.
   */
  at: number;
  /**
   * Human-readable label for the step (usually the node label).
   */
  label: string;
  /**
   * Snapshot of the flow's variable state at the moment this frame was
   * captured. Snapshots are deep-copied at capture time so that subsequent
   * mutations of state do not retroactively mutate prior frames.
   */
  state: Record<string, FlowVariableValue>;
}

export function captureFrame(
  nodeId: string,
  label: string,
  state: Record<string, FlowVariableValue>,
  now: () => number = Date.now,
): FlowFrame {
  return {
    nodeId,
    label,
    at: now(),
    state: cloneState(state),
  };
}

export function cloneState(
  state: Record<string, FlowVariableValue>,
): Record<string, FlowVariableValue> {
  return JSON.parse(JSON.stringify(state)) as Record<string, FlowVariableValue>;
}

export interface VariableDiff {
  key: string;
  before: FlowVariableValue | undefined;
  after: FlowVariableValue | undefined;
  kind: "added" | "removed" | "changed";
}

export function diffFrames(
  before: FlowFrame | undefined,
  after: FlowFrame,
): VariableDiff[] {
  const out: VariableDiff[] = [];
  const beforeState = before?.state ?? {};
  const keys = new Set([
    ...Object.keys(beforeState),
    ...Object.keys(after.state),
  ]);
  for (const key of [...keys].sort()) {
    const a = beforeState[key];
    const b = after.state[key];
    const inA = key in beforeState;
    const inB = key in after.state;
    if (inA && !inB) {
      out.push({ key, before: a, after: undefined, kind: "removed" });
    } else if (!inA && inB) {
      out.push({ key, before: undefined, after: b, kind: "added" });
    } else if (JSON.stringify(a) !== JSON.stringify(b)) {
      out.push({ key, before: a, after: b, kind: "changed" });
    }
  }
  return out;
}

export function formatValue(value: FlowVariableValue | undefined): string {
  if (value === undefined) return "—";
  if (value === null) return "null";
  if (typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

"use client";

import { useMemo, useState } from "react";

import {
  diffFrames,
  type FlowFrame,
  type FlowVariableValue,
  formatValue,
} from "@/lib/flow-inspector";

export interface VariableInspectorProps {
  frames: FlowFrame[];
  /**
   * If set, marks the run as still streaming (e.g. an emulator is currently
   * executing the flow).
   */
  running?: boolean;
}

export function VariableInspector(props: VariableInspectorProps) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  const effectiveIdx = useMemo(() => {
    if (props.frames.length === 0) return null;
    if (selectedIdx !== null && selectedIdx < props.frames.length) {
      return selectedIdx;
    }
    return props.frames.length - 1;
  }, [props.frames.length, selectedIdx]);

  const current = effectiveIdx !== null ? props.frames[effectiveIdx] : null;
  const previous =
    effectiveIdx !== null && effectiveIdx > 0
      ? props.frames[effectiveIdx - 1]
      : undefined;
  const diffs = current && previous ? diffFrames(previous, current) : [];

  return (
    <aside
      aria-label="Variable inspector"
      className="flex w-80 flex-col gap-3 border-l bg-card p-4"
      data-testid="variable-inspector"
    >
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Variable inspector</h2>
        <span
          className={`rounded px-2 py-0.5 text-xs ${props.running ? "border border-success/30 bg-success/10 text-success" : "bg-muted text-muted-foreground"}`}
          data-testid="inspector-status"
        >
          {props.running ? "running" : "idle"}
        </span>
      </header>

      {props.frames.length === 0 ? (
        <p
          className="rounded border border-dashed border-border bg-muted px-3 py-2 text-xs text-muted-foreground"
          data-testid="inspector-empty"
        >
          Run the emulator to capture state at each step.
        </p>
      ) : (
        <>
          <ol
            className="flex max-h-40 flex-col gap-1 overflow-auto rounded border bg-muted p-1 text-xs"
            data-testid="inspector-frames"
          >
            {props.frames.map((f, idx) => {
              const isSelected = idx === effectiveIdx;
              return (
                <li key={`${f.nodeId}-${f.at}-${idx}`}>
                  <button
                    className={`flex w-full items-center justify-between rounded px-2 py-1 text-left ${isSelected ? "border border-info/30 bg-info/10 font-medium text-info" : "hover:bg-card"}`}
                    data-testid={`inspector-frame-${idx}`}
                    onClick={() => setSelectedIdx(idx)}
                    type="button"
                  >
                    <span>
                      <span className="mr-2 font-mono text-muted-foreground">
                        #{idx + 1}
                      </span>
                      {f.label}
                    </span>
                    <span className="font-mono text-muted-foreground">
                      {f.nodeId}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          {current ? (
            <section
              aria-label="Frame state"
              className="flex flex-col gap-2"
              data-testid="inspector-state"
            >
              <h3 className="text-xs uppercase text-muted-foreground">
                state @ {current.label}
              </h3>
              {Object.keys(current.state).length === 0 ? (
                <p
                  className="text-xs text-muted-foreground"
                  data-testid="inspector-state-empty"
                >
                  (no variables defined yet)
                </p>
              ) : (
                <table className="w-full text-xs">
                  <tbody>
                    {Object.keys(current.state)
                      .sort()
                      .map((k) => (
                        <Row
                          key={k}
                          name={k}
                          value={current.state[k] as FlowVariableValue}
                        />
                      ))}
                  </tbody>
                </table>
              )}
            </section>
          ) : null}

          {diffs.length > 0 ? (
            <section
              aria-label="Diff against previous frame"
              className="flex flex-col gap-1"
              data-testid="inspector-diff"
            >
              <h3 className="text-xs uppercase text-muted-foreground">
                changes since previous step
              </h3>
              <ul className="flex flex-col gap-0.5 text-xs">
                {diffs.map((d) => (
                  <li
                    className="flex items-center gap-2 font-mono"
                    data-testid={`inspector-diff-${d.key}`}
                    key={d.key}
                  >
                    <span
                      className={`rounded px-1 ${
                        d.kind === "added"
                          ? "border border-success/30 bg-success/10 text-success"
                          : d.kind === "removed"
                            ? "border border-destructive/30 bg-destructive/10 text-destructive"
                            : "border border-warning/30 bg-warning/10 text-warning"
                      }`}
                    >
                      {d.kind}
                    </span>
                    <span className="font-semibold">{d.key}</span>
                    <span className="text-muted-foreground">
                      {formatValue(d.before)} → {formatValue(d.after)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </aside>
  );
}

function Row({ name, value }: { name: string; value: FlowVariableValue }) {
  return (
    <tr data-testid={`inspector-var-${name}`}>
      <td className="py-0.5 pr-2 font-mono text-muted-foreground">{name}</td>
      <td className="py-0.5 font-mono">{formatValue(value)}</td>
    </tr>
  );
}

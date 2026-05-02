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
      className="flex w-80 flex-col gap-3 border-l bg-white p-4"
      data-testid="variable-inspector"
    >
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Variable inspector</h2>
        <span
          className={`rounded px-2 py-0.5 text-xs ${props.running ? "bg-emerald-100 text-emerald-700" : "bg-zinc-100 text-zinc-600"}`}
          data-testid="inspector-status"
        >
          {props.running ? "running" : "idle"}
        </span>
      </header>

      {props.frames.length === 0 ? (
        <p
          className="rounded border border-dashed border-zinc-200 bg-zinc-50 px-3 py-2 text-xs text-zinc-500"
          data-testid="inspector-empty"
        >
          Run the emulator to capture state at each step.
        </p>
      ) : (
        <>
          <ol
            className="flex max-h-40 flex-col gap-1 overflow-auto rounded border bg-zinc-50 p-1 text-xs"
            data-testid="inspector-frames"
          >
            {props.frames.map((f, idx) => {
              const isSelected = idx === effectiveIdx;
              return (
                <li key={`${f.nodeId}-${f.at}-${idx}`}>
                  <button
                    className={`flex w-full items-center justify-between rounded px-2 py-1 text-left ${isSelected ? "bg-blue-100 font-medium text-blue-900" : "hover:bg-white"}`}
                    data-testid={`inspector-frame-${idx}`}
                    onClick={() => setSelectedIdx(idx)}
                    type="button"
                  >
                    <span>
                      <span className="mr-2 font-mono text-zinc-500">
                        #{idx + 1}
                      </span>
                      {f.label}
                    </span>
                    <span className="font-mono text-zinc-400">
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
              <h3 className="text-xs uppercase text-zinc-500">
                state @ {current.label}
              </h3>
              {Object.keys(current.state).length === 0 ? (
                <p
                  className="text-xs text-zinc-500"
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
              <h3 className="text-xs uppercase text-zinc-500">
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
                          ? "bg-emerald-100 text-emerald-800"
                          : d.kind === "removed"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-amber-100 text-amber-800"
                      }`}
                    >
                      {d.kind}
                    </span>
                    <span className="font-semibold">{d.key}</span>
                    <span className="text-zinc-500">
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
      <td className="py-0.5 pr-2 font-mono text-zinc-500">{name}</td>
      <td className="py-0.5 font-mono">{formatValue(value)}</td>
    </tr>
  );
}

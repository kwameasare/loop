"use client";

import { useState } from "react";

import {
  eventAtPlayhead,
  setPlayhead,
  type PairDebugSession,
} from "@/lib/collaboration";

import { PresenceBar } from "./presence-bar";

interface PairDebugPanelProps {
  session: PairDebugSession;
  onScrub?(playheadMs: number): void;
}

export function PairDebugPanel(props: PairDebugPanelProps): JSX.Element {
  const { session, onScrub } = props;
  const [current, setCurrent] = useState<PairDebugSession>(session);
  const focused = eventAtPlayhead(current);
  const max = current.trace[current.trace.length - 1]?.offsetMs ?? 0;
  const min = current.trace[0]?.offsetMs ?? 0;

  function jumpTo(offsetMs: number): void {
    const next = setPlayhead(current, offsetMs);
    setCurrent(next);
    onScrub?.(next.playheadMs);
  }

  return (
    <section
      data-testid="pair-debug"
      aria-labelledby="pair-debug-title"
      className="rounded-md border border-slate-200 bg-white p-4 space-y-3"
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="pair-debug-title" className="text-sm font-semibold">
          Pair debugging · {current.id}
        </h3>
        <p className="text-xs text-slate-500">Shared trace playhead</p>
      </header>
      <PresenceBar users={current.participants} />
      <div className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs">
        <p data-testid="playhead-readout">
          Playhead: <strong>{current.playheadMs}ms</strong>
          {focused ? ` · ${focused.kind} · ${focused.summary}` : ""}
        </p>
        <input
          type="range"
          min={min}
          max={max}
          step={20}
          value={current.playheadMs}
          onChange={(e) => jumpTo(Number(e.target.value))}
          aria-label="Trace playhead"
          data-testid="playhead-scrubber"
          className="mt-2 w-full"
        />
      </div>
      <ol className="space-y-1" data-testid="trace-events">
        {current.trace.map((ev) => {
          const active = focused?.id === ev.id;
          return (
            <li
              key={ev.id}
              data-testid={`trace-event-${ev.id}`}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
                active
                  ? "border-sky-300 bg-sky-50"
                  : "border-slate-200 bg-white"
              }`}
            >
              <button
                type="button"
                data-testid={`trace-jump-${ev.id}`}
                onClick={() => jumpTo(ev.offsetMs)}
                className="rounded border border-slate-300 bg-white px-1.5 py-0.5 text-[11px] font-mono hover:bg-slate-50"
              >
                {ev.offsetMs}ms
              </button>
              <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide">
                {ev.kind}
              </span>
              <span className="flex-1 text-slate-700">{ev.summary}</span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

"use client";

import { useState } from "react";
import {
  formatDurationNs,
  layoutTrace,
  type Span,
  type Trace,
} from "@/lib/traces";
import { SpanDetail } from "@/components/trace/span-detail";

const KIND_COLOR: Record<Span["kind"], string> = {
  server: "bg-sky-500",
  client: "bg-violet-500",
  internal: "bg-emerald-500",
  producer: "bg-amber-500",
  consumer: "bg-rose-500",
};

const STATUS_RING: Record<Span["status"], string> = {
  ok: "ring-1 ring-transparent",
  error: "ring-2 ring-red-500",
  unset: "ring-1 ring-zinc-300",
};

/**
 * Trace waterfall.
 *
 * Pure presentational: parent fetches the trace; we render the bars,
 * a depth indent, and a sticky right rail with the SpanDetail panel.
 * Click selects a span; default selection is the root.
 */
export function TraceWaterfall({ trace }: { trace: Trace }) {
  const layout = layoutTrace(trace);
  const [selectedId, setSelectedId] = useState<string | null>(
    layout.laidOut[0]?.span.id ?? null,
  );

  const selected =
    layout.laidOut.find((s) => s.span.id === selectedId)?.span ?? null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]" data-testid="trace-waterfall">
      <div className="space-y-1" role="list" aria-label="trace spans">
        <div className="text-muted-foreground flex justify-between px-2 text-xs">
          <span>Span</span>
          <span>{formatDurationNs(layout.duration_ns)} total</span>
        </div>
        {layout.laidOut.map(({ span, depth, offset, width }) => {
          const isSelected = span.id === selectedId;
          return (
            <button
              key={span.id}
              type="button"
              role="listitem"
              data-testid="span-row"
              data-span-id={span.id}
              onClick={() => setSelectedId(span.id)}
              className={`block w-full rounded-md text-left transition-colors ${
                isSelected ? "bg-zinc-100" : "hover:bg-zinc-50"
              }`}
            >
              <div className="flex items-center gap-3 px-2 py-1">
                <span
                  className="w-48 shrink-0 truncate text-sm"
                  style={{ paddingLeft: `${depth * 14}px` }}
                  title={span.name}
                >
                  <span className="text-muted-foreground mr-1 text-xs">
                    {span.service}
                  </span>
                  {span.name}
                </span>
                <div className="bg-muted relative h-3 flex-1 overflow-hidden rounded">
                  <div
                    data-testid="span-bar"
                    className={`absolute h-full rounded ${KIND_COLOR[span.kind]} ${STATUS_RING[span.status]}`}
                    style={{
                      left: `${offset * 100}%`,
                      width: `${width * 100}%`,
                    }}
                  />
                </div>
                <span className="text-muted-foreground w-16 shrink-0 text-right text-xs">
                  {formatDurationNs(span.end_ns - span.start_ns)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
      <aside className="lg:sticky lg:top-4 lg:self-start" data-testid="span-detail-pane">
        {selected ? (
          <SpanDetail span={selected} />
        ) : (
          <p className="text-muted-foreground text-sm">Select a span.</p>
        )}
      </aside>
    </div>
  );
}

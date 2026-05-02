"use client";

import { useMemo, useState } from "react";

import { SpanDetail } from "@/components/trace/span-detail";
import {
  TRACE_CLIENT,
  TRACE_CONSUMER,
  TRACE_INTERNAL,
  TRACE_PRODUCER,
  TRACE_SERVER,
  TRACE_STATUS_ERROR,
  TRACE_STATUS_UNSET,
} from "@/lib/design-tokens";
import {
  formatDurationNs,
  layoutTrace,
  type Span,
  type Trace,
} from "@/lib/traces";

const KIND_FILL: Record<Span["kind"], string> = {
  server: TRACE_SERVER,
  client: TRACE_CLIENT,
  internal: TRACE_INTERNAL,
  producer: TRACE_PRODUCER,
  consumer: TRACE_CONSUMER,
};

const STATUS_STROKE: Record<Span["status"], string> = {
  ok: "transparent",
  error: TRACE_STATUS_ERROR,
  unset: TRACE_STATUS_UNSET,
};

const ROW_HEIGHT = 22;
const BAR_HEIGHT = 12;
const BAR_Y = (ROW_HEIGHT - BAR_HEIGHT) / 2;
const SVG_WIDTH = 600;

/**
 * Trace waterfall rendered as a single inline SVG so 200+ spans stay
 * cheap: one ``<rect>`` per span, no per-row DOM nesting in the bar
 * lane, click-to-expand inline attributes, and a sticky right rail
 * with the SpanDetail panel for tabs/events/raw.
 */
export function TraceWaterfall({ trace }: { trace: Trace }) {
  const layout = useMemo(() => layoutTrace(trace), [trace]);
  const [selectedId, setSelectedId] = useState<string | null>(
    layout.laidOut[0]?.span.id ?? null,
  );

  const selected =
    layout.laidOut.find((s) => s.span.id === selectedId)?.span ?? null;

  const svgHeight = Math.max(ROW_HEIGHT, layout.laidOut.length * ROW_HEIGHT);

  return (
    <div
      className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]"
      data-testid="trace-waterfall"
    >
      <div className="space-y-1" role="list" aria-label="trace spans">
        <div className="text-muted-foreground flex justify-between px-2 text-xs">
          <span>Span</span>
          <span>{formatDurationNs(layout.duration_ns)} total</span>
        </div>
        <div className="flex">
          <ul className="w-56 shrink-0 space-y-0">
            {layout.laidOut.map(({ span, depth }) => {
              const isSelected = span.id === selectedId;
              return (
                <li className="space-y-0" key={span.id}>
                  <button
                    aria-expanded={isSelected}
                    className={`flex w-full items-center text-left text-sm ${
                      isSelected ? "bg-zinc-100" : "hover:bg-zinc-50"
                    }`}
                    data-span-id={span.id}
                    data-testid="span-row"
                    onClick={() => setSelectedId(span.id)}
                    style={{
                      height: `${ROW_HEIGHT}px`,
                      paddingLeft: `${4 + depth * 14}px`,
                    }}
                    type="button"
                  >
                    <span className="text-muted-foreground mr-1 text-xs">
                      {span.service}
                    </span>
                    <span className="truncate" title={span.name}>
                      {span.name}
                    </span>
                  </button>
                  {isSelected ? (
                    <div
                      className="border-l-2 border-zinc-300 bg-zinc-50 px-2 py-1 text-xs"
                      data-testid={`span-attrs-inline-${span.id}`}
                    >
                      {Object.entries(span.attributes).length === 0 ? (
                        <span className="text-muted-foreground">
                          No attributes.
                        </span>
                      ) : (
                        <dl className="grid grid-cols-1 gap-0.5">
                          {Object.entries(span.attributes).map(([k, v]) => (
                            <div className="flex justify-between gap-3" key={k}>
                              <dt className="text-muted-foreground font-mono">
                                {k}
                              </dt>
                              <dd className="font-mono">{String(v)}</dd>
                            </div>
                          ))}
                        </dl>
                      )}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <svg
            aria-label="span timeline"
            className="flex-1"
            data-testid="trace-waterfall-svg"
            height={svgHeight}
            preserveAspectRatio="none"
            role="img"
            viewBox={`0 0 ${SVG_WIDTH} ${svgHeight}`}
            width="100%"
          >
            {layout.laidOut.map(({ span, offset, width }, i) => {
              const x = offset * SVG_WIDTH;
              const w = Math.max(1, width * SVG_WIDTH);
              const y = i * ROW_HEIGHT + BAR_Y;
              return (
                <rect
                  data-span-id={span.id}
                  data-testid="span-bar"
                  fill={KIND_FILL[span.kind]}
                  height={BAR_HEIGHT}
                  key={span.id}
                  onClick={() => setSelectedId(span.id)}
                  rx={2}
                  stroke={STATUS_STROKE[span.status]}
                  strokeWidth={span.status === "error" ? 2 : 1}
                  style={{ cursor: "pointer" }}
                  width={w}
                  x={x}
                  y={y}
                />
              );
            })}
          </svg>
          <div className="w-20 shrink-0">
            {layout.laidOut.map(({ span }) => (
              <div
                className="text-muted-foreground flex items-center justify-end pr-1 text-xs"
                key={`d-${span.id}`}
                style={{ height: `${ROW_HEIGHT}px` }}
              >
                {formatDurationNs(span.end_ns - span.start_ns)}
              </div>
            ))}
          </div>
        </div>
      </div>
      <aside
        className="lg:sticky lg:top-4 lg:self-start"
        data-testid="span-detail-pane"
      >
        {selected ? (
          <SpanDetail span={selected} />
        ) : (
          <p className="text-muted-foreground text-sm">Select a span.</p>
        )}
      </aside>
    </div>
  );
}

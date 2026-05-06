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
  formatUsd,
  layoutTrace,
  type LaidOutSpan,
  type Span,
  type Trace,
  type TraceSpanCategory,
} from "@/lib/traces";

const KIND_FILL: Record<Span["kind"], string> = {
  server: TRACE_SERVER,
  client: TRACE_CLIENT,
  internal: TRACE_INTERNAL,
  producer: TRACE_PRODUCER,
  consumer: TRACE_CONSUMER,
};

const KIND_DASH: Record<Span["kind"], string | undefined> = {
  server: undefined,
  client: "6 3",
  internal: undefined,
  producer: "2 3",
  consumer: "8 2 2 2",
};

const STATUS_STROKE: Record<Span["status"], string> = {
  ok: "transparent",
  error: TRACE_STATUS_ERROR,
  unset: TRACE_STATUS_UNSET,
};

const STATUS_LABEL: Record<Span["status"], string> = {
  ok: "OK",
  error: "Error",
  unset: "Unset",
};

const STATUS_CLASS: Record<Span["status"], string> = {
  ok: "text-success",
  error: "text-destructive",
  unset: "text-muted-foreground",
};

const CATEGORY_LABEL: Record<TraceSpanCategory, string> = {
  llm: "LLM",
  tool: "Tool",
  retrieval: "Retrieval",
  memory: "Memory",
  channel: "Channel",
  voice: "Voice",
  sub_agent: "Sub-agent",
  retry: "Retry",
  provider_failover: "Failover",
  budget: "Budget",
  policy: "Policy",
  eval: "Eval",
  deploy: "Deploy",
};

const CATEGORY_MARK: Record<TraceSpanCategory, string> = {
  llm: "LLM",
  tool: "TL",
  retrieval: "RT",
  memory: "MY",
  channel: "CH",
  voice: "VO",
  sub_agent: "SA",
  retry: "RY",
  provider_failover: "FO",
  budget: "BD",
  policy: "PY",
  eval: "EV",
  deploy: "DP",
};

type SortKey = "start" | "duration" | "status" | "cost";
type SortDirection = "asc" | "desc";
type SpanSort = { key: SortKey; direction: SortDirection };

const ROW_HEIGHT = 28;
const BAR_HEIGHT = 14;
const BAR_Y = (ROW_HEIGHT - BAR_HEIGHT) / 2;
const SVG_WIDTH = 600;

function spanDuration(span: Span): number {
  return span.end_ns - span.start_ns;
}

function spanCost(span: Span): number {
  return span.cost?.total_usd ?? 0;
}

function compareRows(a: LaidOutSpan, b: LaidOutSpan, sort: SpanSort): number {
  const direction = sort.direction === "asc" ? 1 : -1;
  if (sort.key === "start")
    return (a.span.start_ns - b.span.start_ns) * direction;
  if (sort.key === "duration") {
    return (spanDuration(a.span) - spanDuration(b.span)) * direction;
  }
  if (sort.key === "cost")
    return (spanCost(a.span) - spanCost(b.span)) * direction;
  return a.span.status.localeCompare(b.span.status) * direction;
}

function nextSort(current: SpanSort, key: SortKey): SpanSort {
  if (current.key !== key) return { key, direction: "asc" };
  return {
    key,
    direction: current.direction === "asc" ? "desc" : "asc",
  };
}

function sortLabel(sort: SpanSort, key: SortKey): string {
  if (sort.key !== key) return "";
  return sort.direction === "asc" ? " ascending" : " descending";
}

function ariaSort(
  sort: SpanSort,
  key: SortKey,
): "ascending" | "descending" | "none" {
  if (sort.key !== key) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
}

/**
 * Trace waterfall with a keyboard-first span list and a sortable table
 * alternative. The SVG stays lightweight for dense traces, while the
 * textual rows carry category, status, duration, cost, and parent data
 * so meaning never depends on color alone.
 */
export function TraceWaterfall({ trace }: { trace: Trace }) {
  const layout = useMemo(() => layoutTrace(trace), [trace]);
  const [selectedId, setSelectedId] = useState<string | null>(
    layout.laidOut[0]?.span.id ?? null,
  );
  const [sort, setSort] = useState<SpanSort>({
    key: "start",
    direction: "asc",
  });

  const selected =
    layout.laidOut.find((s) => s.span.id === selectedId)?.span ?? null;

  const sortedRows = useMemo(
    () => [...layout.laidOut].sort((a, b) => compareRows(a, b, sort)),
    [layout.laidOut, sort],
  );

  const svgHeight = Math.max(ROW_HEIGHT, layout.laidOut.length * ROW_HEIGHT);

  return (
    <div
      className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(20rem,1fr)]"
      data-testid="trace-waterfall"
    >
      <div className="min-w-0 space-y-4">
        <section
          aria-describedby="trace-waterfall-summary"
          aria-label="Trace waterfall"
          className="rounded-md border bg-card p-3"
        >
          <p className="sr-only" id="trace-waterfall-summary">
            Trace {trace.id} has {layout.laidOut.length} spans over{" "}
            {formatDurationNs(layout.duration_ns)}. Use the span list or the
            sortable table to inspect each span.
          </p>
          <div className="flex items-center justify-between gap-3 px-1 pb-2 text-xs text-muted-foreground">
            <span>Span</span>
            <span>{formatDurationNs(layout.duration_ns)} total</span>
          </div>
          <div className="flex min-w-0 overflow-x-auto">
            <ul className="w-72 shrink-0 space-y-0" role="list">
              {layout.laidOut.map(({ span, depth }) => {
                const isSelected = span.id === selectedId;
                return (
                  <li className="space-y-0" key={span.id}>
                    <button
                      aria-current={isSelected ? "true" : undefined}
                      aria-label={`${span.name}, ${CATEGORY_LABEL[span.category]}, ${STATUS_LABEL[span.status]}, ${formatDurationNs(spanDuration(span))}`}
                      className={`flex w-full items-center gap-2 rounded-sm text-left text-sm target-transition ${
                        isSelected ? "bg-muted" : "hover:bg-muted/60"
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
                      <span className="inline-flex h-5 min-w-8 items-center justify-center rounded border bg-background px-1 font-mono text-[10px]">
                        {CATEGORY_MARK[span.category]}
                      </span>
                      <span
                        className="min-w-0 flex-1 truncate"
                        title={span.name}
                      >
                        {span.name}
                      </span>
                      <span
                        className={`text-xs font-medium ${STATUS_CLASS[span.status]}`}
                      >
                        {STATUS_LABEL[span.status]}
                      </span>
                    </button>
                    {isSelected ? (
                      <div
                        className="border-l-2 bg-muted/40 px-2 py-1 text-xs"
                        data-testid={`span-attrs-inline-${span.id}`}
                      >
                        {Object.entries(span.attributes).length === 0 ? (
                          <span className="text-muted-foreground">
                            No attributes recorded.
                          </span>
                        ) : (
                          <dl className="grid grid-cols-1 gap-0.5">
                            {Object.entries(span.attributes).map(([k, v]) => (
                              <div
                                className="flex justify-between gap-3"
                                key={k}
                              >
                                <dt className="font-mono text-muted-foreground">
                                  {k}
                                </dt>
                                <dd className="truncate font-mono">
                                  {String(v)}
                                </dd>
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
              aria-hidden="true"
              className="min-w-[28rem] flex-1"
              data-testid="trace-waterfall-svg"
              height={svgHeight}
              preserveAspectRatio="none"
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
                    rx={span.kind === "producer" ? 0 : 3}
                    stroke={STATUS_STROKE[span.status]}
                    strokeDasharray={KIND_DASH[span.kind]}
                    strokeWidth={span.status === "error" ? 2 : 1}
                    style={{ cursor: "pointer" }}
                    width={w}
                    x={x}
                    y={y}
                  />
                );
              })}
            </svg>
            <div className="w-24 shrink-0">
              {layout.laidOut.map(({ span }) => (
                <div
                  className="flex items-center justify-end pr-1 text-xs text-muted-foreground"
                  key={`d-${span.id}`}
                  style={{ height: `${ROW_HEIGHT}px` }}
                >
                  {formatDurationNs(spanDuration(span))}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section
          aria-label="Sortable span table alternative"
          className="overflow-x-auto rounded-md border bg-card"
          data-testid="span-table"
        >
          <table className="w-full min-w-[48rem] text-sm">
            <thead className="bg-muted/60 text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2">Span</th>
                <th className="px-3 py-2">Kind</th>
                <th className="px-3 py-2" aria-sort={ariaSort(sort, "start")}>
                  <button
                    className="font-medium"
                    onClick={() =>
                      setSort((current) => nextSort(current, "start"))
                    }
                    type="button"
                  >
                    Start{sortLabel(sort, "start")}
                  </button>
                </th>
                <th
                  className="px-3 py-2"
                  aria-sort={ariaSort(sort, "duration")}
                >
                  <button
                    className="font-medium"
                    onClick={() =>
                      setSort((current) => nextSort(current, "duration"))
                    }
                    type="button"
                  >
                    Duration{sortLabel(sort, "duration")}
                  </button>
                </th>
                <th className="px-3 py-2" aria-sort={ariaSort(sort, "status")}>
                  <button
                    className="font-medium"
                    onClick={() =>
                      setSort((current) => nextSort(current, "status"))
                    }
                    type="button"
                  >
                    Status{sortLabel(sort, "status")}
                  </button>
                </th>
                <th className="px-3 py-2" aria-sort={ariaSort(sort, "cost")}>
                  <button
                    className="font-medium"
                    onClick={() =>
                      setSort((current) => nextSort(current, "cost"))
                    }
                    type="button"
                  >
                    Cost{sortLabel(sort, "cost")}
                  </button>
                </th>
                <th className="px-3 py-2">Parent span</th>
              </tr>
            </thead>
            <tbody>
              {sortedRows.map(({ span }) => (
                <tr
                  className="border-t"
                  data-testid="span-table-row"
                  key={span.id}
                >
                  <td className="px-3 py-2">
                    <button
                      className="font-mono text-xs underline-offset-2 hover:underline"
                      onClick={() => setSelectedId(span.id)}
                      type="button"
                    >
                      {span.name}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    {CATEGORY_LABEL[span.category]} / {span.kind}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {formatDurationNs(span.start_ns - layout.start_ns)}
                  </td>
                  <td className="px-3 py-2">
                    {formatDurationNs(spanDuration(span))}
                  </td>
                  <td
                    className={`px-3 py-2 font-medium ${STATUS_CLASS[span.status]}`}
                  >
                    {STATUS_LABEL[span.status]}
                  </td>
                  <td className="px-3 py-2">{formatUsd(spanCost(span))}</td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {span.parent_id ?? "root"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
      <aside
        className="xl:sticky xl:top-4 xl:self-start"
        data-testid="span-detail-pane"
      >
        {selected ? (
          <SpanDetail span={selected} />
        ) : (
          <p className="text-sm text-muted-foreground">Select a span.</p>
        )}
      </aside>
    </div>
  );
}

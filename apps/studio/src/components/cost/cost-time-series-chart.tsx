"use client";

import { useMemo, useState } from "react";

import {
  buildDailyCostSeries,
  formatDayLabel,
  type DailyCostPoint,
} from "@/lib/cost-series";
import { formatUSD, type UsageRecord } from "@/lib/costs";
import {
  CHART_AXIS_LABEL,
  CHART_GRID,
  CHART_PRIMARY_SERIES,
} from "@/lib/design-tokens";

export interface CostTimeSeriesChartProps {
  records: UsageRecord[];
  workspace_id: string;
  window_start_ms: number;
  window_end_ms: number;
}

const CHART_WIDTH = 720;
const CHART_HEIGHT = 220;
const PADDING = { top: 12, right: 12, bottom: 28, left: 48 };

/**
 * 30-day daily cost line chart with per-agent multi-select and a
 * hover tooltip that breaks down spend by agent for the focused day.
 *
 * The chart is rendered as an inline SVG (no external chart library)
 * so it stays cheap to bundle and trivial to assert against in tests.
 * The series math lives in ``lib/cost-series.ts`` and is unit-tested
 * separately so the rendering layer stays a thin presentation shell.
 */
export function CostTimeSeriesChart(props: CostTimeSeriesChartProps) {
  const fullSeries = useMemo(
    () =>
      buildDailyCostSeries(props.records, {
        workspace_id: props.workspace_id,
        window_start_ms: props.window_start_ms,
        window_end_ms: props.window_end_ms,
      }),
    [
      props.records,
      props.workspace_id,
      props.window_start_ms,
      props.window_end_ms,
    ],
  );
  const [selected, setSelected] = useState<readonly string[]>(() =>
    fullSeries.agents.map((a) => a.agent_id),
  );
  const [focusIdx, setFocusIdx] = useState<number | null>(null);

  const series = useMemo(
    () =>
      buildDailyCostSeries(props.records, {
        workspace_id: props.workspace_id,
        window_start_ms: props.window_start_ms,
        window_end_ms: props.window_end_ms,
        selected_agent_ids: selected,
      }),
    [
      props.records,
      props.workspace_id,
      props.window_start_ms,
      props.window_end_ms,
      selected,
    ],
  );

  const maxCents = Math.max(1, ...series.points.map((p) => p.total_cents));
  const innerWidth = CHART_WIDTH - PADDING.left - PADDING.right;
  const innerHeight = CHART_HEIGHT - PADDING.top - PADDING.bottom;
  const stepX =
    series.points.length > 1
      ? innerWidth / (series.points.length - 1)
      : innerWidth;

  function pointXY(p: DailyCostPoint, i: number): [number, number] {
    const x = PADDING.left + i * stepX;
    const y =
      PADDING.top + innerHeight - (p.total_cents / maxCents) * innerHeight;
    return [x, y];
  }

  const linePath = series.points
    .map((p, i) => {
      const [x, y] = pointXY(p, i);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");

  function toggleAgent(id: string) {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  const focusedPoint = focusIdx === null ? null : series.points[focusIdx];

  return (
    <section
      className="flex flex-col gap-3 rounded-lg border p-4"
      data-testid="cost-time-series-chart"
    >
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Daily cost (last 30 days)</h2>
        <fieldset
          className="flex flex-wrap gap-2"
          data-testid="cost-agent-multiselect"
        >
          <legend className="sr-only">Agents</legend>
          {fullSeries.agents.map((agent) => {
            const checked = selected.includes(agent.agent_id);
            return (
              <label
                className="flex items-center gap-1 text-xs"
                data-testid={`cost-agent-toggle-${agent.agent_id}`}
                key={agent.agent_id}
              >
                <input
                  checked={checked}
                  onChange={() => toggleAgent(agent.agent_id)}
                  type="checkbox"
                />
                <span>{agent.agent_name}</span>
              </label>
            );
          })}
        </fieldset>
      </header>

      <svg
        aria-label="Daily cost time series"
        className="w-full"
        data-testid="cost-chart-svg"
        height={CHART_HEIGHT}
        role="img"
        viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
        width="100%"
      >
        <line
          stroke={CHART_GRID}
          x1={PADDING.left}
          x2={CHART_WIDTH - PADDING.right}
          y1={CHART_HEIGHT - PADDING.bottom}
          y2={CHART_HEIGHT - PADDING.bottom}
        />
        <text
          fill={CHART_AXIS_LABEL}
          fontSize="10"
          textAnchor="end"
          x={PADDING.left - 4}
          y={PADDING.top + 4}
        >
          {formatUSD(maxCents)}
        </text>
        <text
          fill={CHART_AXIS_LABEL}
          fontSize="10"
          textAnchor="end"
          x={PADDING.left - 4}
          y={CHART_HEIGHT - PADDING.bottom}
        >
          $0.00
        </text>
        {series.points.length > 0 ? (
          <path
            d={linePath}
            fill="none"
            stroke={CHART_PRIMARY_SERIES}
            strokeWidth="1.5"
          />
        ) : null}
        {series.points.map((p, i) => {
          const [x, y] = pointXY(p, i);
          return (
            <g key={p.day_ms}>
              <circle
                cx={x}
                cy={y}
                data-testid={`cost-point-${i}`}
                fill={CHART_PRIMARY_SERIES}
                onMouseEnter={() => setFocusIdx(i)}
                onMouseLeave={() => setFocusIdx(null)}
                onFocus={() => setFocusIdx(i)}
                onBlur={() => setFocusIdx(null)}
                r="3"
                tabIndex={0}
              />
            </g>
          );
        })}
        {series.points.map((p, i) =>
          i === 0 ||
          i === series.points.length - 1 ||
          i === Math.floor(series.points.length / 2) ? (
            <text
              fill={CHART_AXIS_LABEL}
              fontSize="10"
              key={`label-${p.day_ms}`}
              textAnchor="middle"
              x={pointXY(p, i)[0]}
              y={CHART_HEIGHT - PADDING.bottom + 14}
            >
              {formatDayLabel(p.day_ms)}
            </text>
          ) : null,
        )}
      </svg>

      {focusedPoint ? (
        <div
          className="rounded border bg-white p-2 text-xs shadow-sm"
          data-testid="cost-tooltip"
        >
          <p className="font-semibold" data-testid="cost-tooltip-day">
            {formatDayLabel(focusedPoint.day_ms)}
          </p>
          <p data-testid="cost-tooltip-total">
            Total: {formatUSD(focusedPoint.total_cents)}
          </p>
          {Object.keys(focusedPoint.by_agent).length === 0 ? (
            <p className="text-muted-foreground">No agent activity.</p>
          ) : (
            <ul>
              {Object.entries(focusedPoint.by_agent).map(([agent_id, cents]) => {
                const agent = fullSeries.agents.find(
                  (a) => a.agent_id === agent_id,
                );
                return (
                  <li
                    data-testid={`cost-tooltip-agent-${agent_id}`}
                    key={agent_id}
                  >
                    {agent?.agent_name ?? agent_id}: {formatUSD(cents)}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      ) : null}
    </section>
  );
}

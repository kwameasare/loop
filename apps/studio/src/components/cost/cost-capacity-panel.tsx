"use client";

import { useMemo, useState } from "react";

import { EvidenceCallout, LiveBadge, StatePanel } from "@/components/target";
import {
  formatPreciseUSD,
  formatUSD,
  type CostCapacityModel,
  type CostLineItem,
  type CostSurface,
} from "@/lib/costs";
import {
  formatMs,
  formatSignedMs,
  formatSignedUsd,
  type LatencyBudgetModel,
  type LatencyBudgetSegment,
} from "@/lib/latency";

export interface CostCapacityPanelProps {
  model: CostCapacityModel;
  latency: LatencyBudgetModel;
}

function surfaceTone(
  surface: CostSurface,
): "live" | "staged" | "canary" | "paused" {
  if (surface.state === "ready") return "live";
  if (surface.state === "degraded") return "canary";
  return "paused";
}

function LineItemRow({ item }: { item: CostLineItem }) {
  return (
    <tr className="border-b last:border-0" data-testid={`cost-line-${item.id}`}>
      <td className="px-3 py-3 align-top font-medium">{item.label}</td>
      <td className="px-3 py-3 align-top text-muted-foreground">
        {item.formula}
      </td>
      <td className="px-3 py-3 text-right align-top tabular-nums">
        {formatPreciseUSD(item.cents)}
      </td>
      <td className="px-3 py-3 align-top text-xs text-muted-foreground">
        {item.evidence}
      </td>
    </tr>
  );
}

function segmentWidth(segment: LatencyBudgetSegment, totalMs: number): string {
  if (totalMs <= 0 || segment.ms <= 0) return "0%";
  return `${Math.max(4, (segment.ms / totalMs) * 100)}%`;
}

export function CostCapacityPanel({ model, latency }: CostCapacityPanelProps) {
  const [targetMs, setTargetMs] = useState(latency.targetMs);
  const overBudgetMs = latency.totalMs - targetMs;
  const targetPercent = Math.max(
    0,
    Math.min(100, (targetMs / Math.max(latency.totalMs, targetMs)) * 100),
  );
  const orderedSuggestions = useMemo(
    () =>
      [...latency.suggestions].sort(
        (a, b) => Math.abs(b.expectedMsDelta) - Math.abs(a.expectedMsDelta),
      ),
    [latency.suggestions],
  );

  return (
    <section className="space-y-6" data-testid="cost-capacity-panel">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Observe / Cost and latency
          </p>
          <h2 className="mt-1 text-xl font-semibold">Cost safety</h2>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            Per-turn, agent, channel, model, tool, retrieval, environment, and
            customer-segment cost stay tied to line-item math before any budget
            decision changes production behavior.
          </p>
        </div>
        <LiveBadge tone={overBudgetMs > 0 ? "canary" : "live"}>
          {overBudgetMs > 0
            ? `${formatMs(overBudgetMs)} over target`
            : "Within target"}
        </LiveBadge>
      </header>

      <div className="grid gap-3 2xl:grid-cols-5">
        {model.surfaces.map((surface) => (
          <article
            className="rounded-md border bg-card p-4"
            data-testid={`cost-surface-${surface.id}`}
            key={surface.id}
          >
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-sm font-semibold">{surface.label}</h3>
              <LiveBadge tone={surfaceTone(surface)}>{surface.state}</LiveBadge>
            </div>
            <p className="mt-3 text-2xl font-semibold tabular-nums">
              {surface.value}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {surface.detail}
            </p>
            <p className="mt-3 text-xs text-muted-foreground">
              Evidence: {surface.evidence}
            </p>
          </article>
        ))}
      </div>

      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <section
          className="rounded-md border bg-card"
          data-testid="cost-line-item-math"
          aria-labelledby="cost-line-item-heading"
        >
          <div className="border-b p-4">
            <h3 className="font-semibold" id="cost-line-item-heading">
              Line-item math
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              This turn cost {formatPreciseUSD(model.totalLineItemCents)}. Every
              production-affecting line is visible, including unsupported
              runtime metering.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 font-semibold" scope="col">
                    Line item
                  </th>
                  <th className="px-3 py-2 font-semibold" scope="col">
                    Math
                  </th>
                  <th
                    className="px-3 py-2 text-right font-semibold"
                    scope="col"
                  >
                    Cost
                  </th>
                  <th className="px-3 py-2 font-semibold" scope="col">
                    Evidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {model.lineItems.map((item) => (
                  <LineItemRow item={item} key={item.id} />
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <EvidenceCallout
          confidence={82}
          confidenceLevel="medium"
          source={model.projectedMonthEndEvidence}
          title="Projected month-end"
          tone="warning"
        >
          Projected month-end is {formatUSD(model.projectedMonthEndCents)}.
          Preview budget cap increases before apply; use a degrade rule when
          quality gates stay green.
        </EvidenceCallout>
      </div>

      <section className="space-y-3" data-testid="cost-decisions">
        <div>
          <h3 className="text-lg font-semibold">Cost decisions</h3>
          <p className="text-sm text-muted-foreground">
            Caps, degrade rules, model comparisons, traffic simulation, tool
            loop detection, campaign estimates, and team attribution carry
            expected effect, risk, and evidence.
          </p>
        </div>
        <div className="grid gap-3 2xl:grid-cols-4">
          {model.decisions.map((decision) => (
            <article
              className="rounded-md border bg-card p-4"
              data-testid={`cost-decision-${decision.id}`}
              key={decision.id}
            >
              <div className="flex items-start justify-between gap-3">
                <h4 className="font-semibold">{decision.label}</h4>
                <LiveBadge
                  tone={decision.state === "ready" ? "live" : "staged"}
                >
                  {decision.state}
                </LiveBadge>
              </div>
              <p className="mt-2 text-sm">{decision.recommendation}</p>
              <dl className="mt-3 space-y-2 text-xs text-muted-foreground">
                <div>
                  <dt className="font-semibold uppercase">Expected effect</dt>
                  <dd>{decision.expectedEffect}</dd>
                </div>
                <div>
                  <dt className="font-semibold uppercase">Risk</dt>
                  <dd>{decision.risk}</dd>
                </div>
                <div>
                  <dt className="font-semibold uppercase">Evidence</dt>
                  <dd>{decision.evidence}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section
        className="space-y-4 rounded-md border bg-card p-4"
        data-testid="latency-budget-visualizer"
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold">Latency budget visualizer</h3>
            <p className="text-sm text-muted-foreground">
              {latency.scenario}. Current total is {formatMs(latency.totalMs)};
              target marker is {formatMs(targetMs)}.
            </p>
          </div>
          <LiveBadge tone={overBudgetMs > 0 ? "canary" : "live"}>
            {overBudgetMs > 0
              ? `${formatMs(overBudgetMs)} to remove`
              : "Budget met"}
          </LiveBadge>
        </div>

        <label className="flex flex-col gap-2 text-sm" htmlFor="latency-target">
          <span className="font-medium">Target marker</span>
          <input
            aria-label="Latency target marker"
            className="w-full"
            id="latency-target"
            max={2500}
            min={400}
            onChange={(event) => setTargetMs(Number(event.target.value))}
            step={50}
            type="range"
            value={targetMs}
          />
        </label>

        <div
          aria-label="Latency budget stacked bar"
          className="relative rounded-md border p-3"
          role="img"
        >
          <div className="flex h-8 overflow-hidden rounded-md bg-muted">
            {latency.segments.map((segment) => (
              <div
                aria-hidden="true"
                className={
                  segment.state === "ready"
                    ? "border-r border-background bg-info/70"
                    : "border-r border-background bg-muted"
                }
                key={segment.id}
                style={{ width: segmentWidth(segment, latency.totalMs) }}
                title={`${segment.label}: ${formatMs(segment.ms)}`}
              />
            ))}
          </div>
          <div
            aria-hidden="true"
            className="absolute top-2 h-10 border-l-2 border-warning"
            style={{ left: `${targetPercent}%` }}
          />
          <dl className="mt-3 grid gap-2 text-xs text-muted-foreground 2xl:grid-cols-3">
            {latency.segments.map((segment) => (
              <div key={segment.id}>
                <dt className="font-semibold text-foreground">
                  {segment.label}
                </dt>
                <dd>
                  {formatMs(segment.ms)}. Evidence: {segment.evidence}
                </dd>
              </div>
            ))}
          </dl>
        </div>

        {overBudgetMs > 0 ? (
          <StatePanel state="stale" title="Latency target needs changes">
            Shrink at least {formatMs(overBudgetMs)} before this scenario meets
            the current marker. Suggestions below show quality, eval, and cost
            impact before apply.
          </StatePanel>
        ) : (
          <StatePanel state="success" title="Latency target is met">
            Keep the current budget and monitor production p95 before reducing
            quality or tool coverage.
          </StatePanel>
        )}

        <div className="grid gap-3 2xl:grid-cols-3">
          {orderedSuggestions.map((suggestion) => (
            <article
              className="rounded-md border p-4"
              data-testid={`latency-suggestion-${suggestion.id}`}
              key={suggestion.id}
            >
              <div className="flex items-start justify-between gap-3">
                <h4 className="font-semibold">{suggestion.label}</h4>
                <LiveBadge
                  tone={suggestion.state === "blocked" ? "canary" : "staged"}
                >
                  {suggestion.state}
                </LiveBadge>
              </div>
              <dl className="mt-3 space-y-2 text-sm">
                <div>
                  <dt className="text-xs font-semibold uppercase text-muted-foreground">
                    Latency
                  </dt>
                  <dd>{formatSignedMs(suggestion.expectedMsDelta)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-muted-foreground">
                    Cost
                  </dt>
                  <dd>{formatSignedUsd(suggestion.costImpactUsd)}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-muted-foreground">
                    Quality
                  </dt>
                  <dd>{suggestion.qualityImpact}</dd>
                </div>
                <div>
                  <dt className="text-xs font-semibold uppercase text-muted-foreground">
                    Eval impact
                  </dt>
                  <dd>{suggestion.evalImpact}</dd>
                </div>
              </dl>
              <p className="mt-3 text-xs text-muted-foreground">
                Evidence: {suggestion.evidence}
              </p>
            </article>
          ))}
        </div>
      </section>
    </section>
  );
}

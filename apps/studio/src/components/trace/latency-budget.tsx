"use client";

import { useEffect, useState } from "react";
import { Gauge } from "lucide-react";

import { EvidenceCallout, LiveBadge } from "@/components/target";
import {
  fetchLatencyBudget,
  type LatencyBudgetModel,
} from "@/lib/trace-insights";
import type { Trace } from "@/lib/traces";
import { cn } from "@/lib/utils";

export function LatencyBudgetVisualizer({
  agentId,
  trace,
}: {
  agentId: string;
  trace: Trace;
}) {
  const [target, setTarget] = useState(900);
  const [model, setModel] = useState<LatencyBudgetModel | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetchLatencyBudget(agentId, trace, target)
      .then((next) => {
        if (!cancelled) {
          setModel(next);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load latency budget.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, trace, target]);

  const total = model?.total_latency_ms ?? 0;
  const overBudget = model ? model.gap_ms > 0 : false;

  return (
    <section
      className="space-y-4 instrument-panel rounded-2xl p-4"
      data-testid="latency-budget-visualizer"
      aria-labelledby="latency-budget-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Latency budget visualizer
          </p>
          <h2 className="mt-1 text-lg font-semibold" id="latency-budget-heading">
            Where the turn spends time
          </h2>
        </div>
        <LiveBadge tone={overBudget ? "canary" : "live"}>
          {total} ms / {target} ms
        </LiveBadge>
      </div>
      <label className="block text-xs font-medium">
        Target latency: {target} ms
        <input
          className="mt-2 w-full accent-primary"
          type="range"
          min={300}
          max={2500}
          step={50}
          value={target}
          onChange={(event) => setTarget(Number(event.target.value))}
          data-testid="latency-budget-target"
        />
      </label>
      {error ? (
        <p
          className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      {model ? (
        <>
          {model.unavailable_reason ? (
            <p
              className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
              data-testid="latency-budget-unavailable"
              role="status"
            >
              {model.unavailable_reason}
            </p>
          ) : null}
          <div className="flex h-5 overflow-hidden rounded-full bg-muted">
            {model.spans.map((span) => (
              <span
                key={span.id}
                className={cn(
                  "border-r border-background last:border-r-0",
                  span.kind === "model"
                    ? "bg-info"
                    : span.kind === "tool"
                      ? "bg-warning"
                      : span.kind === "retrieval"
                        ? "bg-success"
                        : "bg-muted-foreground",
                )}
                style={{
                  width: `${Math.max(5, (span.ms / Math.max(1, total)) * 100)}%`,
                }}
                title={`${span.label}: ${span.ms} ms`}
              />
            ))}
          </div>
          {model.suggestions.length > 0 ? (
            <div className="grid gap-2 md:grid-cols-3">
              {model.suggestions.map((suggestion) => (
                <EvidenceCallout
                  key={suggestion.id}
                  title={suggestion.label}
                  source={suggestion.evidence_ref}
                  confidence={86}
                  tone={suggestion.quality_delta < -0.03 ? "warning" : "info"}
                >
                  <span className="inline-flex items-center gap-2">
                    <Gauge className="h-4 w-4" aria-hidden />
                    Saves {suggestion.saves_ms} ms; quality delta{" "}
                    {suggestion.quality_delta}
                  </span>
                </EvidenceCallout>
              ))}
            </div>
          ) : (
            <p
              className="rounded-md border bg-background p-3 text-sm text-muted-foreground"
              data-testid="latency-budget-no-suggestions"
            >
              No latency optimization suggestions are shown until span-level
              model, retrieval, tool, memory, and channel timings are available
              for this trace.
            </p>
          )}
        </>
      ) : null}
    </section>
  );
}

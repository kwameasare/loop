"use client";

import { useEffect, useState } from "react";

import { LiveBadge } from "@/components/target";
import {
  fetchContextAblation,
  type ContextAblationItem,
} from "@/lib/trace-insights";

const DEFAULT_TOGGLES: Record<string, boolean> = {
  prompt_sections: true,
  kb_chunks: true,
  memory: true,
  examples: true,
};

export function CostOfContextSlider({
  agentId,
  turnId,
}: {
  agentId: string;
  turnId: string;
}) {
  const [toggles, setToggles] = useState(DEFAULT_TOGGLES);
  const [items, setItems] = useState<ContextAblationItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [unavailableReason, setUnavailableReason] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    void fetchContextAblation(agentId, turnId, toggles)
      .then((next) => {
        if (!cancelled) {
          setItems(next.items);
          setUnavailableReason(next.unavailable_reason ?? null);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load context ablation.",
          );
          setUnavailableReason(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, turnId, toggles]);

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="cost-of-context-slider"
      aria-labelledby="cost-of-context-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Cost of context
          </p>
          <h2 className="mt-1 text-lg font-semibold" id="cost-of-context-heading">
            Toggle context and compare the delta
          </h2>
        </div>
        <LiveBadge tone={items.length > 0 ? "staged" : error ? "paused" : "draft"}>
          {items.length} ablations
        </LiveBadge>
      </div>
      {error ? (
        <p
          className="mt-4 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      {unavailableReason ? (
        <p
          className="mt-4 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning"
          data-testid="context-ablation-unavailable"
          role="status"
        >
          {unavailableReason}
        </p>
      ) : null}
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <label
            key={item.id}
            className="rounded-md border bg-background p-3 text-sm"
          >
            <span className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={toggles[item.id] ?? item.enabled}
                onChange={(event) =>
                  setToggles((current) => ({
                    ...current,
                    [item.id]: event.target.checked,
                  }))
                }
                data-testid={`context-toggle-${item.id}`}
              />
              <span>
                <span className="block font-medium">{item.label}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  Cost {item.cost_delta_pct}% · latency {item.latency_delta_ms} ms · quality{" "}
                  {item.quality_delta}
                </span>
                <span className="mt-1 block font-mono text-[11px] text-muted-foreground">
                  {item.evidence_ref}
                </span>
              </span>
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { LiveBadge } from "@/components/target/live-badge";
import { RiskHalo } from "@/components/target/risk-halo";
import { cn } from "@/lib/utils";
import {
  AUTO_ROLLBACK_TRIGGERS,
  CANARY_METRICS,
  CANARY_STAGES,
  type CanaryPercent,
} from "@/lib/deploy-flight";

function MetricValue({ value, unit }: { value: number; unit: string }) {
  const formatted = new Intl.NumberFormat("en", {
    maximumFractionDigits: 3,
  }).format(value);
  return (
    <span className="font-semibold tabular-nums">
      {formatted}
      {unit}
    </span>
  );
}

export interface CanarySliderProps {
  defaultPercent?: CanaryPercent;
  onChange?: (next: CanaryPercent) => void;
}

export function CanarySlider({
  defaultPercent = 10,
  onChange,
}: CanarySliderProps) {
  const [percent, setPercent] = useState<CanaryPercent>(defaultPercent);
  const handle = (next: CanaryPercent) => {
    setPercent(next);
    onChange?.(next);
  };
  const anyFiring = AUTO_ROLLBACK_TRIGGERS.some((t) => t.firing);
  return (
    <section className="space-y-3" data-testid="canary-slider">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Canary rollout</h2>
        <LiveBadge tone={anyFiring ? "paused" : "canary"} pulse={!anyFiring}>
          {percent}% live
        </LiveBadge>
      </header>
      <div
        role="radiogroup"
        aria-label="Canary traffic share"
        className="grid gap-2 sm:grid-cols-4"
        data-testid="canary-stage-list"
      >
        {CANARY_STAGES.map((stage) => {
          const active = stage === percent;
          return (
            <button
              key={stage}
              type="button"
              role="radio"
              aria-checked={active}
              onClick={() => handle(stage)}
              data-testid={`canary-stage-${stage}`}
              className={cn(
                "rounded-md border bg-card px-3 py-2 text-sm font-medium transition",
                active
                  ? "border-primary ring-1 ring-primary"
                  : "hover:border-foreground/40",
              )}
            >
              {stage}%
            </button>
          );
        })}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <article
          className="rounded-md border bg-card p-3"
          data-testid="canary-metrics"
        >
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Live vs production baseline
          </h3>
          <ul className="mt-2 space-y-2">
            {CANARY_METRICS.map((m) => (
              <li
                key={m.id}
                className="flex items-center justify-between text-sm"
                data-testid={`canary-metric-${m.id}`}
              >
                <span>{m.label}</span>
                <span
                  className={cn(
                    "flex items-baseline gap-2 font-mono text-xs",
                    m.healthier ? "text-success" : "text-warning",
                  )}
                  data-healthier={m.healthier}
                >
                  <MetricValue value={m.current} unit={m.unit} />
                  <span className="text-muted-foreground">
                    base {m.baseline}
                    {m.unit}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </article>

        <article
          className="rounded-md border bg-card p-3"
          data-testid="auto-rollback-triggers"
        >
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Auto-rollback triggers
          </h3>
          <ul className="mt-2 space-y-2">
            {AUTO_ROLLBACK_TRIGGERS.map((t) => (
              <li
                key={t.id}
                data-testid={`auto-rollback-${t.id}`}
                data-firing={t.firing}
              >
                <RiskHalo level={t.firing ? "blocked" : t.armed ? "low" : "none"}>
                  <div className="flex items-center justify-between p-2 text-xs">
                    <div>
                      <p className="font-medium">{t.label}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">
                        threshold {t.threshold} · current {t.current}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "rounded-md border px-2 py-0.5 font-medium",
                        t.firing
                          ? "border-destructive bg-destructive/10 text-destructive"
                          : "border-success/40 bg-success/10 text-success",
                      )}
                    >
                      {t.firing ? "firing" : "armed"}
                    </span>
                  </div>
                </RiskHalo>
              </li>
            ))}
          </ul>
        </article>
      </div>

      <div className="flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={percent === 100}
          onClick={() => {
            const idx = CANARY_STAGES.indexOf(percent);
            const next = CANARY_STAGES[Math.min(idx + 1, CANARY_STAGES.length - 1)];
            if (next !== undefined && next !== percent) handle(next);
          }}
          data-testid="canary-advance"
        >
          {percent === 100 ? "Fully live" : "Advance to next stage"}
        </Button>
      </div>
    </section>
  );
}

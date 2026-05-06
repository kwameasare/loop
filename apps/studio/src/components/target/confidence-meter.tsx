import {
  CONFIDENCE_TREATMENTS,
  type ConfidenceLevel,
} from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

export interface ConfidenceMeterProps {
  value: number;
  level?: ConfidenceLevel;
  label?: string;
  evidence?: string;
  className?: string;
}

function levelForValue(value: number): ConfidenceLevel {
  if (value >= 85) return "high";
  if (value >= 65) return "medium";
  if (value >= 35) return "low";
  return "unsupported";
}

function clampPercent(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export function ConfidenceMeter({
  value,
  level,
  label,
  evidence,
  className,
}: ConfidenceMeterProps) {
  const percent = clampPercent(value);
  const resolvedLevel = level ?? levelForValue(percent);
  const treatment = CONFIDENCE_TREATMENTS[resolvedLevel];
  return (
    <div className={cn("space-y-2", className)} data-testid="confidence-meter">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="font-medium">{label ?? treatment.label}</span>
        <span className={cn("font-semibold tabular-nums", treatment.textClassName)}>
          {percent}%
        </span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-muted"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent}
        aria-label={label ?? treatment.label}
      >
        <div
          className={cn("h-full rounded-full", treatment.barClassName)}
          style={{ width: `${percent}%` }}
        />
      </div>
      {evidence ? (
        <p className="text-xs text-muted-foreground">{evidence}</p>
      ) : null}
    </div>
  );
}

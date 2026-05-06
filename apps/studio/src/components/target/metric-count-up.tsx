import { cn } from "@/lib/utils";

export interface MetricCountUpProps {
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  delta?: string;
  formatter?: Intl.NumberFormat;
  className?: string;
}

const DEFAULT_FORMATTER = new Intl.NumberFormat("en", {
  maximumFractionDigits: 2,
});

export function MetricCountUp({
  label,
  value,
  suffix,
  prefix,
  delta,
  formatter = DEFAULT_FORMATTER,
  className,
}: MetricCountUpProps) {
  return (
    <div className={cn("rounded-md border bg-card p-4", className)} data-testid="metric-count-up">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">
        {prefix}
        {formatter.format(value)}
        {suffix}
      </p>
      {delta ? <p className="mt-1 text-xs text-muted-foreground">{delta}</p> : null}
    </div>
  );
}

import { cn } from "@/lib/utils";

export type SkeletonShape = "trace" | "conversation" | "eval" | "chart";

export interface CharacterSkeletonProps {
  shape: SkeletonShape;
  rows?: number;
  className?: string;
}

const SHAPE_LABELS: Record<SkeletonShape, string> = {
  trace: "Loading trace",
  conversation: "Loading conversation",
  eval: "Loading eval suite",
  chart: "Loading chart",
};

/**
 * Skeletons that mimic actual content structure (§29.9). Never a generic gray
 * box. Pulse is gated behind `motion-safe` so reduced-motion users see a
 * static placeholder.
 */
export function CharacterSkeleton({
  shape,
  rows = 4,
  className,
}: CharacterSkeletonProps): JSX.Element {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label={SHAPE_LABELS[shape]}
      data-testid={`skeleton-${shape}`}
      className={cn("rounded-md border border-border bg-card p-3", className)}
    >
      {shape === "trace" ? (
        <div className="space-y-2">
          <div
            data-testid="skeleton-time-axis"
            className="h-1 w-full rounded bg-muted-foreground/20"
          />
          {Array.from({ length: rows }).map((_, idx) => (
            <div
              key={idx}
              data-testid="skeleton-trace-row"
              className="motion-safe:animate-pulse h-3 rounded bg-muted-foreground/20"
              style={{ width: `${50 + ((idx * 37) % 50)}%` }}
            />
          ))}
        </div>
      ) : null}
      {shape === "conversation" ? (
        <div className="space-y-2">
          {Array.from({ length: rows }).map((_, idx) => (
            <div
              key={idx}
              data-testid="skeleton-conv-row"
              className={cn(
                "motion-safe:animate-pulse h-4 rounded bg-muted-foreground/20",
                idx % 2 === 0 ? "ml-auto w-3/5" : "w-2/3",
              )}
            />
          ))}
        </div>
      ) : null}
      {shape === "eval" ? (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground" data-testid="skeleton-case-count">
            {rows} cases queued
          </div>
          <div className="grid grid-cols-3 gap-2">
            {Array.from({ length: rows }).map((_, idx) => (
              <div
                key={idx}
                className="motion-safe:animate-pulse h-12 rounded bg-muted-foreground/20"
              />
            ))}
          </div>
        </div>
      ) : null}
      {shape === "chart" ? (
        <div className="space-y-2">
          <div className="flex items-end gap-1" data-testid="skeleton-axes">
            {Array.from({ length: rows }).map((_, idx) => (
              <div
                key={idx}
                className="motion-safe:animate-pulse w-4 rounded-t bg-muted-foreground/20"
                style={{ height: `${24 + ((idx * 53) % 36)}px` }}
              />
            ))}
          </div>
          <div className="h-px w-full bg-muted-foreground/30" />
        </div>
      ) : null}
    </div>
  );
}

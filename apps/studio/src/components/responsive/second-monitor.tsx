"use client";

import {
  SECOND_MONITOR_PANES,
  SECOND_MONITOR_PANE_LABELS,
} from "@/lib/responsive";
import { cn } from "@/lib/utils";

export interface SecondMonitorProps {
  className?: string;
  /**
   * Optional content per pane. When omitted the pane shows a placeholder
   * preview, which keeps the second-monitor layout testable in isolation.
   */
  children?: Partial<Record<(typeof SECOND_MONITOR_PANES)[number], React.ReactNode>>;
}

export function SecondMonitor({ className, children }: SecondMonitorProps) {
  return (
    <section
      aria-label="Second monitor"
      data-testid="second-monitor"
      className={cn(
        "grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-4",
        className,
      )}
    >
      {SECOND_MONITOR_PANES.map((pane) => (
        <article
          key={pane}
          data-testid={`second-monitor-${pane}`}
          className="flex min-h-[160px] flex-col rounded-md border border-border bg-card p-3"
        >
          <header className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">
            {SECOND_MONITOR_PANE_LABELS[pane]}
          </header>
          <div className="flex-1 text-xs text-muted-foreground">
            {children?.[pane] ?? (
              <p>
                {SECOND_MONITOR_PANE_LABELS[pane]} stays visible without
                stealing focus from the main editor (§31.4).
              </p>
            )}
          </div>
        </article>
      ))}
    </section>
  );
}

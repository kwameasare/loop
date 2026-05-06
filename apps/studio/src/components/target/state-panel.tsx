import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type StatePanelState =
  | "loading"
  | "empty"
  | "error"
  | "degraded"
  | "stale"
  | "permission"
  | "success";

const STATE_CLASS: Record<StatePanelState, string> = {
  loading: "border-info/30 bg-info/5",
  empty: "border-border bg-card",
  error: "border-destructive/40 bg-destructive/5",
  degraded: "border-warning/50 bg-warning/5",
  stale: "border-warning/40 bg-warning/5",
  permission: "border-border bg-muted/40",
  success: "border-success/40 bg-success/5",
};

export interface StatePanelProps {
  state: StatePanelState;
  title: string;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function StatePanel({
  state,
  title,
  children,
  action,
  className,
}: StatePanelProps) {
  return (
    <section
      className={cn("rounded-md border p-4", STATE_CLASS[state], className)}
      data-state={state}
      data-testid="state-panel"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <div className="mt-1 text-sm text-muted-foreground">{children}</div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </section>
  );
}

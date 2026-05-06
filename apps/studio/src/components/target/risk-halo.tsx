import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type RiskHaloLevel = "none" | "low" | "medium" | "high" | "blocked";

const LEVEL_CLASS: Record<RiskHaloLevel, string> = {
  none: "ring-1 ring-border",
  low: "ring-1 ring-info/40",
  medium: "ring-2 ring-warning/50",
  high: "ring-2 ring-destructive/50",
  blocked: "ring-2 ring-destructive shadow-sm",
};

export interface RiskHaloProps {
  level: RiskHaloLevel;
  label?: string;
  children: ReactNode;
  className?: string;
}

export function RiskHalo({ level, label, children, className }: RiskHaloProps) {
  return (
    <div
      className={cn("rounded-md", LEVEL_CLASS[level], className)}
      data-risk={level}
      data-testid="risk-halo"
      aria-label={label ?? `Risk level: ${level}`}
    >
      {children}
    </div>
  );
}

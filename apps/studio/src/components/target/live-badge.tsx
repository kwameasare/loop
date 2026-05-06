import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type LiveBadgeTone = "live" | "draft" | "staged" | "canary" | "paused";

const TONE_CLASS: Record<LiveBadgeTone, string> = {
  live: "border-success bg-success/10 text-success",
  draft: "border-border bg-muted text-muted-foreground",
  staged: "border-info bg-info/10 text-info",
  canary: "border-warning bg-warning/10 text-warning",
  paused: "border-border bg-background text-muted-foreground",
};

export interface LiveBadgeProps {
  tone?: LiveBadgeTone;
  children: ReactNode;
  pulse?: boolean;
  className?: string;
}

export function LiveBadge({
  tone = "live",
  children,
  pulse = false,
  className,
}: LiveBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center gap-2 rounded-md border px-2.5 text-xs font-medium",
        TONE_CLASS[tone],
        className,
      )}
      data-testid="live-badge"
    >
      <span
        aria-hidden="true"
        className={cn(
          "h-1.5 w-1.5 rounded-full bg-current",
          pulse ? "animate-pulse" : "",
        )}
      />
      {children}
    </span>
  );
}

import type { ReactNode } from "react";

import type { ConfidenceLevel } from "@/lib/design-tokens";
import { cn } from "@/lib/utils";

import { ConfidenceMeter } from "./confidence-meter";

type EvidenceTone = "neutral" | "success" | "warning" | "danger" | "info";

const TONE_CLASS: Record<EvidenceTone, string> = {
  neutral: "border-border bg-card",
  success: "border-success/40 bg-success/5",
  warning: "border-warning/50 bg-warning/5",
  danger: "border-destructive/40 bg-destructive/5",
  info: "border-info/40 bg-info/5",
};

export interface EvidenceCalloutProps {
  title: string;
  children: ReactNode;
  source?: string;
  confidence?: number;
  confidenceLevel?: ConfidenceLevel;
  tone?: EvidenceTone;
  className?: string;
}

export function EvidenceCallout({
  title,
  children,
  source,
  confidence,
  confidenceLevel,
  tone = "neutral",
  className,
}: EvidenceCalloutProps) {
  return (
    <aside
      className={cn("rounded-md border p-4", TONE_CLASS[tone], className)}
      data-testid="evidence-callout"
    >
      <div className="flex flex-col gap-3">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          <div className="mt-1 text-sm text-muted-foreground">{children}</div>
        </div>
        {typeof confidence === "number" ? (
          <ConfidenceMeter
            value={confidence}
            label="Evidence confidence"
            {...(confidenceLevel ? { level: confidenceLevel } : {})}
          />
        ) : null}
        {source ? (
          <p className="text-xs text-muted-foreground">Source: {source}</p>
        ) : null}
      </div>
    </aside>
  );
}

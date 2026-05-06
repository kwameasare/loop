import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

export interface CompletionMarkProps {
  label: string;
  proofHref?: string;
  className?: string;
}

/**
 * A restrained proof moment (§29.10 CompletionMark): tiny check + label, with
 * an optional anchor that links to the canonical proof. No confetti, no
 * fireworks, no particles (§29.3).
 */
export function CompletionMark({
  label,
  proofHref,
  className,
}: CompletionMarkProps): JSX.Element {
  return (
    <span
      role="status"
      data-testid="completion-mark"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-success/30",
        "bg-success/5 px-2 py-1 text-xs text-success",
        className,
      )}
    >
      <Check aria-hidden="true" className="h-3.5 w-3.5" />
      <span>{label}</span>
      {proofHref ? (
        <a
          data-testid="completion-mark-proof"
          href={proofHref}
          className="underline-offset-2 hover:underline"
        >
          proof
        </a>
      ) : null}
    </span>
  );
}

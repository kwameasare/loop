import { DIFF_MARKERS, type DiffKind } from "@/lib/a11y";
import { cn } from "@/lib/utils";

const TONE_CLASSES: Record<(typeof DIFF_MARKERS)[DiffKind]["tone"], string> = {
  ok: "text-success",
  danger: "text-destructive",
  muted: "text-muted-foreground",
};

export interface DiffLineProps {
  kind: DiffKind;
  children: string;
  className?: string;
}

/**
 * Renders a diff line with a `+` / `-` / `·` text prefix in addition to the
 * tone token, so that achromatopsic users still see the change (§30.4).
 */
export function DiffLine({ kind, children, className }: DiffLineProps): JSX.Element {
  const marker = DIFF_MARKERS[kind];
  return (
    <div
      data-testid={`diff-line-${kind}`}
      data-diff={kind}
      className={cn(
        "flex items-baseline gap-2 font-mono text-xs",
        TONE_CLASSES[marker.tone],
        className,
      )}
    >
      <span aria-hidden="true" className="w-3 text-right">
        {marker.prefix}
      </span>
      <span className="sr-only">{marker.label}: </span>
      <span className="flex-1">{children}</span>
    </div>
  );
}

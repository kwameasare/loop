import { cn } from "@/lib/utils";

export interface DiffRibbonProps {
  label: string;
  before: string;
  after: string;
  impact?: string;
  className?: string;
}

export function DiffRibbon({
  label,
  before,
  after,
  impact,
  className,
}: DiffRibbonProps) {
  return (
    <div
      className={cn("overflow-hidden rounded-md border bg-card", className)}
      data-testid="diff-ribbon"
    >
      <div className="border-b bg-muted/70 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="grid gap-px bg-border sm:grid-cols-2">
        <div className="bg-card p-3">
          <p className="text-xs font-medium text-muted-foreground">Before</p>
          <p className="mt-1 text-sm">{before}</p>
        </div>
        <div className="bg-card p-3">
          <p className="text-xs font-medium text-muted-foreground">After</p>
          <p className="mt-1 text-sm">{after}</p>
        </div>
      </div>
      {impact ? (
        <p className="border-t px-3 py-2 text-xs text-muted-foreground">
          {impact}
        </p>
      ) : null}
    </div>
  );
}

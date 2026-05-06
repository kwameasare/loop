import type { TargetSnapshot } from "@/lib/target-ux";
import { cn } from "@/lib/utils";

import { LiveBadge } from "./live-badge";

export interface SnapshotCardProps {
  snapshot: TargetSnapshot;
  className?: string;
}

export function SnapshotCard({ snapshot, className }: SnapshotCardProps) {
  return (
    <article
      className={cn("rounded-md border bg-card p-4", className)}
      data-testid="snapshot-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{snapshot.name}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {snapshot.version} - {snapshot.id}
          </p>
        </div>
        <LiveBadge tone={snapshot.signed ? "staged" : "draft"}>
          {snapshot.signed ? "Signed" : "Draft"}
        </LiveBadge>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{snapshot.summary}</p>
    </article>
  );
}

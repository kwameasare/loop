import { LiveBadge } from "@/components/target";
import { targetUxFixtures } from "@/lib/target-ux";

export function StatusFooter() {
  const workspace = targetUxFixtures.workspace;
  return (
    <footer
      className="border-t bg-background px-4 py-2"
      aria-label="Studio system status"
      data-testid="status-footer"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <div className="flex flex-wrap items-center gap-2">
          <LiveBadge tone="live" className="h-6">
            Control plane healthy
          </LiveBadge>
          <LiveBadge tone="staged" className="h-6">
            {workspace.region}
          </LiveBadge>
          <span>Environment: {workspace.environment}</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span>Branch: {workspace.branch}</span>
          <span>Snapshot: snap_refund_may</span>
        </div>
      </div>
    </footer>
  );
}

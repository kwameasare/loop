import { ConfidenceMeter, DiffRibbon, LiveBadge } from "@/components/target";
import { targetUxFixtures } from "@/lib/target-ux";

export function LivePreviewRail() {
  const agent = targetUxFixtures.agents[0]!;
  const trace = targetUxFixtures.traces[0]!;
  const deploy = targetUxFixtures.deploys[0]!;
  return (
    <aside
      className="border-t bg-surface/70 p-4 lg:border-l lg:border-t-0"
      aria-label="Live preview and inspector"
      data-testid="live-preview-rail"
    >
      <div className="flex h-full min-h-0 flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Live preview
            </p>
            <h2 className="mt-1 text-sm font-semibold">{agent.name}</h2>
          </div>
          <LiveBadge tone="canary" pulse>
            Canary {deploy.canaryPercent}%
          </LiveBadge>
        </div>

        <div className="rounded-md border bg-card p-3">
          <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
            <span>Channel</span>
            <span className="font-medium text-foreground">Web chat</span>
          </div>
          <div className="mt-3 space-y-2 text-sm">
            <p className="rounded-md bg-muted p-2">
              I need to cancel my annual renewal. What happens now?
            </p>
            <p className="rounded-md border border-info/30 bg-info/5 p-2">
              I can help. The May refund policy applies to this renewal, and I
              need one order lookup before I quote the exact window.
            </p>
          </div>
        </div>

        <ConfidenceMeter
          value={agent.evalPassRate}
          label="Current draft coverage"
          evidence="Production replay and migration parity suites included."
        />

        <DiffRibbon
          label="Draft vs production"
          before="Archived refund policy can win retrieval on cancellation phrasing."
          after="May policy is pinned when renewal intent is present."
          impact="One Spanish paraphrase still blocks promotion."
        />

        <div className="mt-auto rounded-md border bg-card p-3 text-xs text-muted-foreground">
          <p className="font-medium text-foreground">Trace ready</p>
          <p className="mt-1">
            {trace.id} - {trace.spans.length} spans - forkable from every span.
          </p>
        </div>
      </div>
    </aside>
  );
}

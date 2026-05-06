import { cn } from "@/lib/utils";
import { DEPLOY_TIMELINE } from "@/lib/deploy-flight";

const STATUS_TONE: Record<string, string> = {
  passed: "border-success/40 bg-success/10 text-success",
  active: "border-info/40 bg-info/10 text-info",
  waiting: "border-border bg-muted text-muted-foreground",
  locked: "border-border bg-card text-muted-foreground",
  failed: "border-destructive bg-destructive/10 text-destructive",
};

export function DeployTimeline() {
  return (
    <section className="space-y-3" data-testid="deploy-timeline">
      <header>
        <h2 className="text-sm font-semibold">Deploy timeline</h2>
        <p className="text-xs text-muted-foreground">
          Build → scan → evals → smoke → canary → production. Every row links to
          its evidence.
        </p>
      </header>
      <ol className="space-y-1.5" data-testid="deploy-timeline-list">
        {DEPLOY_TIMELINE.map((row) => (
          <li
            key={row.id}
            data-testid={`deploy-timeline-${row.id}`}
            className="flex items-center justify-between rounded-md border bg-card px-3 py-2 text-sm"
          >
            <span className="flex items-center gap-3">
              <span className="font-mono text-xs text-muted-foreground">
                {row.id}
              </span>
              <span className="font-medium">{row.label}</span>
            </span>
            <span className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">{row.detail}</span>
              <span
                className={cn(
                  "rounded-md border px-2 py-0.5 text-[11px] font-medium",
                  STATUS_TONE[row.status] ?? STATUS_TONE.locked,
                )}
              >
                {row.status}
              </span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

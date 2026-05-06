import { LiveBadge } from "@/components/target";
import { targetUxFixtures } from "@/lib/target-ux";

const TIMELINE_ITEMS = [
  {
    id: "draft",
    label: "Draft edited",
    detail: "Refund behavior now cites May policy first.",
    tone: "draft" as const,
  },
  {
    id: "replay",
    label: "Replay queued",
    detail: "100 high-risk production turns selected.",
    tone: "staged" as const,
  },
  {
    id: "canary",
    label: "Canary held",
    detail: "Waiting on Release Manager approval.",
    tone: "canary" as const,
  },
];

export function ActivityTimeline() {
  const migration = targetUxFixtures.migrations[0]!;
  return (
    <section
      className="border-t bg-surface-elevated px-4 py-3"
      aria-label="Activity timeline"
      data-testid="activity-timeline"
    >
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Timeline
          </p>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Botpress parity {migration.parityScore}% - {migration.unmappedItems} unmapped items
          </p>
        </div>
        <ol className="grid gap-2 sm:grid-cols-3 xl:min-w-[42rem]">
          {TIMELINE_ITEMS.map((item) => (
            <li key={item.id} className="rounded-md border bg-card p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{item.label}</p>
                <LiveBadge tone={item.tone} className="h-5 px-1.5 text-[0.65rem]">
                  {item.id}
                </LiveBadge>
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{item.detail}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

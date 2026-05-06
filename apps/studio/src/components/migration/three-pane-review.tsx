import { ConfidenceMeter, RiskHalo } from "@/components/target";
import {
  REVIEW_ITEMS,
  type ReviewDecisionSeverity,
  type ReviewItem,
} from "@/lib/migration";
import { cn } from "@/lib/utils";

const SEVERITY_LABEL: Record<ReviewDecisionSeverity, string> = {
  blocking: "Blocking",
  advisory: "Advisory",
  fyi: "FYI",
};

const SEVERITY_TONE: Record<
  ReviewDecisionSeverity,
  "high" | "medium" | "low"
> = {
  blocking: "high",
  advisory: "medium",
  fyi: "low",
};

const SEVERITY_BADGE: Record<ReviewDecisionSeverity, string> = {
  blocking: "border-destructive/40 bg-destructive/10 text-destructive",
  advisory: "border-warning/40 bg-warning/10 text-warning-foreground",
  fyi: "border-info/40 bg-info/10 text-info-foreground",
};

export interface ThreePaneReviewProps {
  items?: readonly ReviewItem[];
  className?: string;
}

/**
 * Three-pane migration review (canonical §18.4). The middle pane is the
 * workbench: every card asks one question and offers one concrete action.
 * The source pane is read-only legacy structure; the Loop pane is the
 * generated, editable result. We never collapse the three views into one.
 */
export function ThreePaneReview({
  items = REVIEW_ITEMS,
  className,
}: ThreePaneReviewProps) {
  return (
    <section
      className={cn("flex flex-col gap-4", className)}
      data-testid="three-pane-review"
      aria-labelledby="three-pane-review-heading"
    >
      <header>
        <h2 id="three-pane-review-heading" className="text-lg font-semibold">
          Source · Needs your eyes · Loop
        </h2>
        <p className="text-sm text-muted-foreground">
          Original structure on the left, decisions in the middle, generated
          Loop agent on the right. Approving a decision updates only the Loop
          pane — the source archive stays read-only forever.
        </p>
      </header>

      <ol
        role="list"
        className="flex flex-col gap-4"
        data-testid="three-pane-review-list"
      >
        {items.map((item) => (
          <li key={item.id} data-testid={`review-item-${item.id}`}>
            <RiskHalo
              level={SEVERITY_TONE[item.severity]}
              label={`Severity ${SEVERITY_LABEL[item.severity]}`}
            >
              <article className="grid gap-px overflow-hidden rounded-md border border-border bg-border md:grid-cols-3">
                <div
                  className="flex flex-col gap-2 bg-card p-4"
                  data-pane="source"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Source · read-only
                  </p>
                  <p className="text-sm">{item.sourceSummary}</p>
                  <p className="mt-auto text-xs text-muted-foreground">
                    Source ID: <code>{item.sourceId}</code>
                  </p>
                </div>

                <div
                  className="flex flex-col gap-3 bg-card p-4"
                  data-pane="needs-eyes"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      Needs your eyes
                    </p>
                    <span
                      className={cn(
                        "rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                        SEVERITY_BADGE[item.severity],
                      )}
                      data-testid={`review-severity-${item.id}`}
                    >
                      {SEVERITY_LABEL[item.severity]}
                    </span>
                  </div>
                  <p className="text-sm font-medium">{item.question}</p>
                  <p className="text-sm text-muted-foreground">{item.action}</p>
                  {item.evidence ? (
                    <p
                      className="text-xs text-muted-foreground"
                      data-testid={`review-evidence-${item.id}`}
                    >
                      Evidence: {item.evidence}
                    </p>
                  ) : null}
                  <ConfidenceMeter
                    value={item.confidence}
                    label="Migration confidence"
                  />
                </div>

                <div
                  className="flex flex-col gap-2 bg-card p-4"
                  data-pane="loop"
                >
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Loop · editable
                  </p>
                  <p className="text-sm">{item.loopSummary}</p>
                  <p className="mt-auto text-xs text-muted-foreground">
                    Lineage preserved. Reverting reattaches the source mapping.
                  </p>
                </div>
              </article>
            </RiskHalo>
          </li>
        ))}
      </ol>
    </section>
  );
}

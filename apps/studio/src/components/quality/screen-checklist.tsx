"use client";

import { useState } from "react";
import { CheckCircle2, Circle, ExternalLink } from "lucide-react";

import {
  QUALITY_CATEGORIES,
  QUALITY_CATEGORY_ANCHORS,
  QUALITY_CATEGORY_LABELS,
  QUALITY_CHECKLIST,
  type ScreenQualityReport,
  scoreScreen,
  toggleChecklistItem,
} from "@/lib/quality";
import { cn } from "@/lib/utils";

export interface ScreenChecklistProps {
  initial: ScreenQualityReport;
  className?: string;
  onChange?: (report: ScreenQualityReport) => void;
}

export function ScreenChecklist({ initial, className, onChange }: ScreenChecklistProps) {
  const [report, setReport] = useState(initial);
  const score = scoreScreen(report);

  const handleToggle = (id: string) => {
    setReport((cur) => {
      const next = toggleChecklistItem(cur, id);
      onChange?.(next);
      return next;
    });
  };

  const itemsByCategory = QUALITY_CATEGORIES.map((cat) => ({
    category: cat,
    items: QUALITY_CHECKLIST.filter((i) => i.category === cat),
  }));

  return (
    <section
      className={cn("flex flex-col gap-4 rounded-md border border-border bg-card p-5", className)}
      data-testid="screen-checklist"
      aria-label={`Review checklist for ${report.screen}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-mono text-xs text-muted-foreground">{report.screen}</p>
          <h2 className="mt-1 text-base font-semibold">
            {report.area || "Untitled area"}
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Reviewed by {report.reviewer} on {report.reviewedAt}
          </p>
        </div>
        <div
          className="rounded-md border border-border bg-background px-3 py-2 text-xs"
          data-testid="checklist-score"
        >
          <p className="font-medium">
            {score.passedItems} / {score.totalItems} items pass
          </p>
          <p
            className={cn(
              "mt-0.5",
              score.meetsNorthStar ? "text-success" : "text-warning",
            )}
          >
            {score.meetsNorthStar ? "Meets north-star" : "Below north-star bar"}
          </p>
        </div>
      </header>

      {itemsByCategory.map(({ category, items }) => {
        const result = report.results.find((r) => r.category === category)!;
        const failing = result.failed.length > 0;
        return (
          <section
            key={category}
            data-testid={`checklist-category-${category}`}
            className={cn(
              "rounded-md border p-3",
              failing ? "border-warning/60 bg-warning/5" : "border-border",
            )}
          >
            <header className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium">
                {QUALITY_CATEGORY_LABELS[category]}{" "}
                <span className="text-muted-foreground">
                  {QUALITY_CATEGORY_ANCHORS[category]}
                </span>
              </h3>
              <span className="text-xs text-muted-foreground">
                {result.passed.length} / {items.length}
              </span>
            </header>
            {failing ? (
              <p
                className="mt-2 flex items-center gap-1 text-xs text-warning"
                data-testid={`checklist-evidence-${category}`}
              >
                <ExternalLink aria-hidden="true" className="h-3 w-3" />
                Evidence: {result.evidence}
              </p>
            ) : null}
            <ul className="mt-2 flex flex-col gap-1">
              {items.map((item) => {
                const checked = result.passed.includes(item.id);
                return (
                  <li key={item.id}>
                    <label
                      className="flex items-start gap-2 text-xs"
                      data-testid={`checklist-item-${item.id}`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => handleToggle(item.id)}
                        className="mt-0.5"
                      />
                      <span
                        className={cn(
                          "flex items-center gap-1.5",
                          checked ? "text-foreground" : "text-muted-foreground",
                        )}
                      >
                        {checked ? (
                          <CheckCircle2 aria-hidden="true" className="h-3.5 w-3.5 text-success" />
                        ) : (
                          <Circle aria-hidden="true" className="h-3.5 w-3.5" />
                        )}
                        {item.prompt}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}

      {report.notes ? (
        <p className="rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">
          {report.notes}
        </p>
      ) : null}
    </section>
  );
}

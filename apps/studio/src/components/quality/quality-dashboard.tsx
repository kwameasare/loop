"use client";

import { useMemo, useState } from "react";

import { LiveBadge } from "@/components/target";
import {
  QUALITY_CATEGORIES,
  QUALITY_CATEGORY_ANCHORS,
  QUALITY_CATEGORY_LABELS,
  type ScreenQualityReport,
  rollupReports,
  scoreScreen,
} from "@/lib/quality";
import { cn } from "@/lib/utils";

export interface QualityDashboardProps {
  reports: readonly ScreenQualityReport[];
  className?: string;
  onSelect?: (report: ScreenQualityReport) => void;
}

export function QualityDashboard({ reports, className, onSelect }: QualityDashboardProps) {
  const rollup = useMemo(() => rollupReports(reports), [reports]);
  const [filter, setFilter] = useState<"all" | "failing">("all");

  const visible = useMemo(() => {
    return reports.filter((r) => {
      if (filter === "failing") return !scoreScreen(r).meetsNorthStar;
      return true;
    });
  }, [reports, filter]);

  return (
    <section
      className={cn("flex flex-col gap-5", className)}
      data-testid="quality-dashboard"
      aria-label="Target UX quality bar dashboard"
    >
      <header>
        <h1 className="text-xl font-semibold">Quality bar</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Tracks each Studio screen against the seven categories from §37 of the
          target UX standard. A screen meets north-star quality only when it
          fails at most one category.
        </p>
      </header>

      <dl
        className="grid grid-cols-2 gap-3 sm:grid-cols-4"
        data-testid="quality-summary"
      >
        <Stat label="Screens reviewed" value={String(rollup.totalScreens)} />
        <Stat
          label="Meeting north-star"
          value={`${rollup.meetingNorthStar} / ${rollup.totalScreens}`}
        />
        <Stat
          label="Coverage ratio"
          value={
            rollup.totalScreens === 0
              ? "—"
              : `${Math.round((rollup.meetingNorthStar / rollup.totalScreens) * 100)}%`
          }
        />
        <Stat
          label="Reviewers"
          value={String(Object.keys(rollup.reviewerCoverage).length)}
        />
      </dl>

      <section
        aria-label="Failing categories"
        className="rounded-md border border-border bg-card p-4"
      >
        <h2 className="text-sm font-medium">Failing screens by category</h2>
        <ul
          className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="quality-category-rollup"
        >
          {QUALITY_CATEGORIES.map((cat) => {
            const failing = rollup.failingByCategory[cat];
            return (
              <li
                key={cat}
                className={cn(
                  "flex items-center justify-between rounded-sm border px-3 py-2 text-xs",
                  failing > 0
                    ? "border-warning bg-warning/10 text-warning"
                    : "border-border bg-background text-muted-foreground",
                )}
                data-testid={`quality-category-${cat}`}
              >
                <span>
                  <span className="font-medium text-foreground">
                    {QUALITY_CATEGORY_LABELS[cat]}
                  </span>
                  <span className="ml-2 text-muted-foreground">
                    {QUALITY_CATEGORY_ANCHORS[cat]}
                  </span>
                </span>
                <span aria-label={`${failing} failing`}>{failing}</span>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="flex items-center gap-2 text-sm">
        <span className="text-muted-foreground">Show:</span>
        <button
          type="button"
          onClick={() => setFilter("all")}
          aria-pressed={filter === "all"}
          className={cn(
            "h-8 rounded-md border px-3 text-xs",
            filter === "all"
              ? "border-focus bg-focus/10"
              : "border-border bg-background text-muted-foreground",
          )}
          data-testid="quality-filter-all"
        >
          All ({reports.length})
        </button>
        <button
          type="button"
          onClick={() => setFilter("failing")}
          aria-pressed={filter === "failing"}
          className={cn(
            "h-8 rounded-md border px-3 text-xs",
            filter === "failing"
              ? "border-focus bg-focus/10"
              : "border-border bg-background text-muted-foreground",
          )}
          data-testid="quality-filter-failing"
        >
          Failing only ({rollup.totalScreens - rollup.meetingNorthStar})
        </button>
      </div>

      {visible.length === 0 ? (
        <p
          role="status"
          className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
          data-testid="quality-empty"
        >
          No screens match this filter. Either every reviewed screen meets the
          bar, or no reviews exist yet.
        </p>
      ) : (
        <ul
          className="flex flex-col gap-2"
          data-testid="quality-screen-list"
        >
          {visible.map((report) => (
            <li key={report.screen}>
              <ScreenRow
                report={report}
                {...(onSelect ? { onSelect } : {})}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface StatProps {
  label: string;
  value: string;
}

function Stat({ label, value }: StatProps) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 text-base font-semibold">{value}</dd>
    </div>
  );
}

interface ScreenRowProps {
  report: ScreenQualityReport;
  onSelect?: (report: ScreenQualityReport) => void;
}

function ScreenRow({ report, onSelect }: ScreenRowProps) {
  const score = scoreScreen(report);
  const tone = score.meetsNorthStar ? "live" : "canary";
  return (
    <button
      type="button"
      onClick={() => onSelect?.(report)}
      className="flex w-full items-center justify-between gap-3 rounded-md border border-border bg-card p-3 text-left transition-colors duration-swift ease-standard hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      data-testid={`quality-row-${report.screen}`}
    >
      <div className="flex flex-col gap-1">
        <span className="font-mono text-xs text-muted-foreground">
          {report.screen}
        </span>
        <span className="text-sm font-medium">
          {report.area || "Untitled area"} ·{" "}
          <span className="text-muted-foreground">
            {report.reviewer} · {report.reviewedAt}
          </span>
        </span>
        {score.failing.length > 0 ? (
          <span className="text-xs text-warning">
            Failing: {score.failing.map((c) => QUALITY_CATEGORY_LABELS[c]).join(", ")}
          </span>
        ) : null}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-xs text-muted-foreground">
          {score.passedItems} / {score.totalItems}
        </span>
        <LiveBadge tone={tone}>
          {score.meetsNorthStar ? "North-star" : "Below bar"}
        </LiveBadge>
      </div>
    </button>
  );
}

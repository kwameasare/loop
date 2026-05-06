"use client";

import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import {
  MIGRATION_SOURCES,
  type MigrationSource,
  type MigrationSourceStatus,
  SOURCE_STATUS_TREATMENT,
} from "@/lib/migration";

const STATUS_BADGE_CLASS: Record<MigrationSourceStatus, string> = {
  verified: "border-success/40 bg-success/10 text-success-foreground",
  planned: "border-info/40 bg-info/10 text-info-foreground",
  aspirational: "border-warning/40 bg-warning/10 text-warning-foreground",
};

const STATUS_FILTER_ORDER: MigrationSourceStatus[] = [
  "verified",
  "planned",
  "aspirational",
];

export interface SourceGridProps {
  sources?: readonly MigrationSource[];
  className?: string;
  onSelect?: (source: MigrationSource) => void;
}

/**
 * Supported sources grid (canonical §18.2). Every source advertises its
 * implementation status with a non-celebratory badge so a builder can never
 * mistake an aspirational target for a verified import.
 */
export function SourceGrid({
  sources = MIGRATION_SOURCES,
  className,
  onSelect,
}: SourceGridProps) {
  const [activeStatus, setActiveStatus] = useState<
    MigrationSourceStatus | "all"
  >("all");

  const filtered = useMemo(() => {
    if (activeStatus === "all") return sources;
    return sources.filter((s) => s.status === activeStatus);
  }, [activeStatus, sources]);

  return (
    <section
      id="sources"
      className={cn("flex flex-col gap-4", className)}
      data-testid="source-grid"
      aria-labelledby="source-grid-heading"
    >
      <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 id="source-grid-heading" className="text-lg font-semibold">
            Supported sources
          </h2>
          <p className="text-sm text-muted-foreground">
            Verified sources have a tested importer. Planned and aspirational
            sources require additional work before parity is provable.
          </p>
        </div>
        <div
          role="radiogroup"
          aria-label="Filter sources by status"
          className="flex flex-wrap gap-2"
        >
          <button
            type="button"
            role="radio"
            aria-checked={activeStatus === "all"}
            onClick={() => setActiveStatus("all")}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium",
              activeStatus === "all"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-muted-foreground",
            )}
            data-testid="source-filter-all"
          >
            All
          </button>
          {STATUS_FILTER_ORDER.map((status) => (
            <button
              key={status}
              type="button"
              role="radio"
              aria-checked={activeStatus === status}
              onClick={() => setActiveStatus(status)}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium",
                activeStatus === status
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border bg-card text-muted-foreground",
              )}
              data-testid={`source-filter-${status}`}
            >
              {SOURCE_STATUS_TREATMENT[status].label}
            </button>
          ))}
        </div>
      </header>

      <ul
        className="grid gap-3 md:grid-cols-2 xl:grid-cols-3"
        data-testid="source-grid-list"
      >
        {filtered.map((source) => {
          const treatment = SOURCE_STATUS_TREATMENT[source.status];
          return (
            <li key={source.id}>
              <article
                data-testid={`source-card-${source.id}`}
                data-status={source.status}
                className="flex h-full flex-col gap-3 rounded-md border border-border bg-card p-4"
              >
                <header className="flex items-start justify-between gap-3">
                  <h3 className="text-base font-semibold">{source.name}</h3>
                  <span
                    className={cn(
                      "shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
                      STATUS_BADGE_CLASS[source.status],
                    )}
                    data-testid={`source-status-${source.id}`}
                  >
                    {treatment.label}
                  </span>
                </header>
                <dl className="space-y-1 text-xs text-muted-foreground">
                  <div>
                    <dt className="inline font-medium text-foreground">
                      Typical input:{" "}
                    </dt>
                    <dd className="inline">{source.typicalInput}</dd>
                  </div>
                  <div>
                    <dt className="inline font-medium text-foreground">
                      Loop goal:{" "}
                    </dt>
                    <dd className="inline">{source.loopGoal}</dd>
                  </div>
                </dl>
                <p className="text-xs text-muted-foreground">
                  {treatment.description}
                </p>
                <div className="mt-auto flex flex-wrap items-center justify-between gap-2">
                  {source.externalDocs ? (
                    <a
                      href={source.externalDocs}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="text-xs font-medium text-primary underline-offset-4 hover:underline"
                    >
                      Reference docs
                    </a>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      Reference docs not yet published
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => onSelect?.(source)}
                    disabled={source.status === "aspirational"}
                    className={cn(
                      "rounded-md border px-3 py-1 text-xs font-semibold",
                      source.status === "aspirational"
                        ? "cursor-not-allowed border-border bg-muted text-muted-foreground"
                        : "border-primary bg-primary/5 text-primary hover:bg-primary/10",
                    )}
                    data-testid={`source-select-${source.id}`}
                    aria-disabled={source.status === "aspirational"}
                  >
                    {source.status === "aspirational"
                      ? "Request partnership"
                      : "Start import"}
                  </button>
                </div>
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

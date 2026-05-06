import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import {
  type MigrationEntryChoice,
  MIGRATION_ENTRY_CHOICES,
} from "@/lib/migration";
import { cn } from "@/lib/utils";

export interface MigrationEntryProps {
  choices?: readonly MigrationEntryChoice[];
  className?: string;
}

/**
 * Migration entry surface (canonical §18.1). Import is rendered first and at
 * larger emphasis so it never feels secondary; the other three choices are
 * available but visually subordinate.
 */
export function MigrationEntry({
  choices = MIGRATION_ENTRY_CHOICES,
  className,
}: MigrationEntryProps) {
  const sorted = [...choices].sort((a, b) =>
    a.firstClass === b.firstClass ? 0 : a.firstClass ? -1 : 1,
  );
  return (
    <section
      className={cn("grid gap-3 lg:grid-cols-2", className)}
      data-testid="migration-entry"
      aria-labelledby="migration-entry-heading"
    >
      <h2 id="migration-entry-heading" className="sr-only">
        Choose how to start
      </h2>
      {sorted.map((choice) => {
        const isFirst = choice.firstClass;
        return (
          <article
            key={choice.id}
            data-testid={`migration-entry-${choice.id}`}
            data-first-class={isFirst ? "true" : "false"}
            className={cn(
              "flex flex-col justify-between gap-4 rounded-lg border p-5",
              isFirst
                ? "border-primary/40 bg-primary/5 lg:col-span-2 lg:p-6"
                : "border-border bg-card",
            )}
          >
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                {isFirst ? "Recommended" : "Alternative"}
              </p>
              <h3
                className={cn(
                  "mt-1 font-semibold tracking-tight",
                  isFirst ? "text-2xl" : "text-base",
                )}
              >
                {choice.label}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground">{choice.summary}</p>
            </div>
            <Link
              href={choice.href}
              className={buttonVariants({
                variant: isFirst ? "default" : "outline",
                size: isFirst ? "lg" : "default",
              })}
              data-testid={`migration-entry-cta-${choice.id}`}
            >
              {isFirst ? "Start import" : "Choose"}
            </Link>
          </article>
        );
      })}
    </section>
  );
}

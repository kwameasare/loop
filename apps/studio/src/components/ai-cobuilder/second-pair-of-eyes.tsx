"use client";

import { useMemo } from "react";

import {
  type AdversarialReview,
  ReviewShapeError,
  blockingBullets,
  validateAdversarialReview,
} from "@/lib/ai-cobuilder";

interface SecondPairOfEyesProps {
  review: AdversarialReview;
}

const SEVERITY_STYLE: Record<string, string> = {
  info: "border-border bg-background text-foreground",
  warn: "border-warning/40 bg-warning/10 text-warning",
  block: "border-destructive/40 bg-destructive/10 text-destructive",
};

export function SecondPairOfEyes({
  review,
}: SecondPairOfEyesProps): JSX.Element {
  const shapeError = useMemo<string | null>(() => {
    try {
      validateAdversarialReview(review);
      return null;
    } catch (e) {
      if (e instanceof ReviewShapeError) {
        return e.message;
      }
      throw e;
    }
  }, [review]);

  const blockers = useMemo(() => blockingBullets(review), [review]);

  return (
    <section
      data-testid={`second-pair-${review.actionId}`}
      className="space-y-3 rounded-md border bg-card p-4"
    >
      <header className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Second Pair of Eyes · adversarial review
        </p>
        {blockers.length > 0 ? (
          <p
            data-testid={`second-pair-blocked-${review.actionId}`}
            className="rounded-full border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-[10px] font-semibold text-destructive"
          >
            {blockers.length} blocker{blockers.length === 1 ? "" : "s"}
          </p>
        ) : null}
      </header>

      {shapeError ? (
        <p
          data-testid={`second-pair-shape-error-${review.actionId}`}
          className="rounded border border-destructive/40 bg-destructive/10 px-2 py-1 text-xs text-destructive"
        >
          {shapeError}
        </p>
      ) : null}

      <ul className="space-y-1">
        {review.bullets.map((b, i) => (
          <li
            key={b.id}
            data-testid={`second-pair-bullet-${b.id}`}
            className={`rounded border px-2 py-1 text-xs ${
              SEVERITY_STYLE[b.severity] ?? SEVERITY_STYLE.info
            }`}
          >
            <span className="mr-2 font-semibold">{i + 1}.</span>
            <span className="mr-2 inline-block rounded-full border px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
              {b.severity}
            </span>
            <span>{b.body}</span>
            <span
              data-testid={`second-pair-evidence-${b.id}`}
              className="ml-2 font-mono text-[10px] text-muted-foreground"
            >
              [{b.evidenceRef}]
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

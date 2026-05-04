/**
 * P0.3: shared loading + error states for App Router section
 * boundaries.
 *
 * Each top-level section (inbox, billing, costs, …) needs a
 * ``loading.tsx`` + ``error.tsx`` so React Suspense + error
 * boundaries don't fall through to the root error page when a fetch
 * suspends or throws. The components are intentionally minimal so
 * the section title stays in the loading/error surface — it gives
 * the operator context about *which* part of the studio is in
 * trouble.
 */

import { Button } from "@/components/ui/button";

export interface SectionLoadingProps {
  /** Section title shown above the skeleton ("Costs", "Inbox", etc.). */
  title: string;
  /** Optional sub-line. */
  subtitle?: string;
}

export function SectionLoading({ title, subtitle }: SectionLoadingProps) {
  return (
    <main
      className="container mx-auto flex max-w-3xl flex-col gap-4 p-6"
      data-testid="section-loading"
    >
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {subtitle ? (
          <p className="text-muted-foreground text-sm">{subtitle}</p>
        ) : null}
      </header>
      <div className="space-y-2">
        <div className="h-12 rounded border bg-muted" />
        <div className="h-12 rounded border bg-muted" />
        <div className="h-12 rounded border bg-muted" />
      </div>
    </main>
  );
}

export interface SectionErrorProps {
  title: string;
  reset: () => void;
  /** Optional override for the body copy. */
  description?: string;
  /** Error object from Next.js route boundary (may include request_id). */
  error?: unknown;
}

function requestIdFromError(error: unknown): string {
  if (!error || typeof error !== "object") return "unknown";
  const record = error as Record<string, unknown>;
  const requestId =
    record.request_id ?? record.requestId ?? record.digest ?? record.requestid;
  return typeof requestId === "string" && requestId.length > 0
    ? requestId
    : "unknown";
}

function reportHref(title: string, requestId: string): string {
  const body = [
    `section=${title}`,
    `request_id=${requestId}`,
    "please include what you were doing when this happened",
  ].join("\n");
  return `mailto:support@loop.dev?subject=${encodeURIComponent(
    `[Studio] ${title} load failure`,
  )}&body=${encodeURIComponent(body)}`;
}

export function SectionError({
  title,
  reset,
  description,
  error,
}: SectionErrorProps) {
  const requestId = requestIdFromError(error);
  return (
    <main
      className="container mx-auto flex max-w-3xl flex-col gap-4 p-6"
      data-testid="section-error"
    >
      <div className="rounded-lg border p-4" role="alert">
        <h2 className="text-base font-medium">{title} could not load</h2>
        <p className="text-muted-foreground mt-1 text-sm">
          {description ??
            "The cp-api request failed. Retry, or sign back in if the session expired."}
        </p>
        <p className="mt-2 text-xs text-muted-foreground" data-testid="section-error-request-id">
          request_id: {requestId}
        </p>
        <div className="mt-4 flex items-center gap-2">
          <Button onClick={reset} variant="outline">
            Retry
          </Button>
          <a
            className="text-sm underline underline-offset-2"
            data-testid="section-error-report"
            href={reportHref(title, requestId)}
          >
            Report
          </a>
        </div>
      </div>
    </main>
  );
}

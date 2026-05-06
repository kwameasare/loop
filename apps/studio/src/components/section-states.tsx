/**
 * Shared target states for App Router section boundaries.
 *
 * Each top-level section (inbox, billing, costs, …) needs a
 * ``loading.tsx`` + ``error.tsx`` so React Suspense + error
 * boundaries don't fall through to the root error page when a fetch
 * suspends or throws. These wrappers keep the state copy, i18n keys,
 * non-color cues, and recovery actions consistent across surfaces.
 */

import {
  TargetState,
  getSectionStateCopy,
  type TargetStateKind,
} from "@/components/target/state";

export interface SectionLoadingProps {
  /** Section title shown above the skeleton ("Costs", "Inbox", etc.). */
  title: string;
  /** Optional sub-line. */
  subtitle?: string | undefined;
  /** Named loading stage, such as "Querying recent traces". */
  stage?: string | undefined;
}

export function SectionLoading({
  title,
  subtitle,
  stage,
}: SectionLoadingProps) {
  const copy = getSectionStateCopy("loading", { section: title, stage });
  return (
    <main
      className="container mx-auto flex max-w-3xl flex-col gap-4 p-6"
      data-testid="section-loading"
    >
      <TargetState
        state="loading"
        objectName={title}
        title={copy.title}
        description={subtitle ?? copy.description}
        stage={stage}
      />
    </main>
  );
}

export interface SectionErrorProps {
  title: string;
  reset: () => void;
  /** Optional override for the body copy. */
  description?: string | undefined;
  /** Error object from Next.js route boundary (may include request_id). */
  error?: unknown | undefined;
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
  const copy = getSectionStateCopy("error", {
    section: title,
    requestId,
  });
  return (
    <main
      className="container mx-auto flex max-w-3xl flex-col gap-4 p-6"
      data-testid="section-error"
    >
      <TargetState
        state="error"
        objectName={title}
        title={copy.title}
        description={description ?? copy.description}
        requestId={requestId}
        primaryAction={{ label: copy.primaryAction, onClick: reset }}
        secondaryAction={{
          label: copy.secondaryAction,
          href: reportHref(title, requestId),
        }}
      />
    </main>
  );
}

export interface SectionStateProps {
  title: string;
  state: Exclude<TargetStateKind, "loading" | "error">;
  description?: string | undefined;
  evidence?: string | undefined;
  stage?: string | undefined;
  updatedAt?: string | undefined;
  primaryAction?:
    | {
        label?: string | undefined;
        onClick?: (() => void) | undefined;
        href?: string | undefined;
      }
    | undefined;
  secondaryAction?:
    | {
        label?: string | undefined;
        onClick?: (() => void) | undefined;
        href?: string | undefined;
      }
    | undefined;
}

export function SectionState({
  title,
  state,
  description,
  evidence,
  stage,
  updatedAt,
  primaryAction,
  secondaryAction,
}: SectionStateProps) {
  const copy = getSectionStateCopy(state, {
    section: title,
    stage,
    updatedAt,
  });
  return (
    <TargetState
      state={state}
      objectName={title}
      title={copy.title}
      description={description ?? copy.description}
      evidence={evidence}
      stage={stage}
      updatedAt={updatedAt}
      primaryAction={primaryAction}
      secondaryAction={secondaryAction}
    />
  );
}

export function SectionEmpty(props: Omit<SectionStateProps, "state">) {
  return <SectionState {...props} state="empty" />;
}

export function SectionDegraded(props: Omit<SectionStateProps, "state">) {
  return <SectionState {...props} state="degraded" />;
}

export function SectionStale(props: Omit<SectionStateProps, "state">) {
  return <SectionState {...props} state="stale" />;
}

export function SectionPermissionBlocked(
  props: Omit<SectionStateProps, "state">,
) {
  return <SectionState {...props} state="permissionBlocked" />;
}

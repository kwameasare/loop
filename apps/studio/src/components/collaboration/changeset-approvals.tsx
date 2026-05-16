"use client";

import {
  isChangesetReadyToMerge,
  pendingAxes,
  validateChangesetApprovals,
  type ApprovalState,
  type Changeset,
} from "@/lib/collaboration";

interface ChangesetApprovalsProps {
  changeset: Changeset;
  onMerge?(cs: Changeset): void;
}

const STATE_TONE: Record<ApprovalState, string> = {
  approved: "border-success bg-success/10 text-success",
  rejected: "border-destructive bg-destructive/10 text-destructive",
  changes_requested: "border-warning bg-warning/10 text-warning",
  pending: "border-border bg-muted text-muted-foreground",
};

export function ChangesetApprovals(
  props: ChangesetApprovalsProps,
): JSX.Element {
  const { changeset, onMerge } = props;
  let validationError: string | null = null;
  try {
    validateChangesetApprovals(changeset);
  } catch (err) {
    validationError = err instanceof Error ? err.message : "invalid";
  }
  const ready = !validationError && isChangesetReadyToMerge(changeset);
  const blocked = pendingAxes(changeset);

  return (
    <section
      data-testid={`changeset-${changeset.id}`}
      aria-labelledby={`changeset-title-${changeset.id}`}
      className="space-y-3 instrument-panel rounded-2xl p-4"
    >
      <header className="space-y-1">
        <h3
          id={`changeset-title-${changeset.id}`}
          className="text-sm font-semibold"
        >
          {changeset.title}
        </h3>
        <p className="text-xs text-muted-foreground">
          By {changeset.authorDisplay} · {changeset.createdAt}
        </p>
      </header>
      {validationError ? (
        <p
          data-testid={`changeset-validation-${changeset.id}`}
          className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive"
        >
          {validationError}
        </p>
      ) : null}
      <ul className="grid gap-2 sm:grid-cols-2">
        {changeset.approvals.map((a) => (
          <li
            key={a.axis}
            data-testid={`approval-${a.axis}`}
            className={`rounded-md border px-3 py-2 text-xs ${STATE_TONE[a.state]}`}
          >
            <p className="text-sm font-medium capitalize">{a.axis}</p>
            <p className="text-[11px] uppercase tracking-wide">{a.state.replace("_", " ")}</p>
            {a.reviewer ? (
              <p className="mt-1 text-[11px]">
                Reviewer: {a.reviewer}
                {a.decidedAt ? ` · ${a.decidedAt}` : ""}
              </p>
            ) : null}
            {a.rationale ? (
              <p className="mt-1">{a.rationale}</p>
            ) : null}
            {a.invalidatedAt ? (
              <p
                className="mt-1 rounded border border-warning/40 bg-warning/10 px-2 py-1 text-warning"
                data-testid={`approval-invalidated-${a.axis}`}
              >
                Approval invalidated by edit · {a.invalidatedAt}
              </p>
            ) : null}
            <p className="mt-1 truncate text-[11px] opacity-70">
              {a.evidenceRef}
            </p>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <p
          data-testid={`changeset-blocked-${changeset.id}`}
          className="text-xs text-muted-foreground"
        >
          {ready
            ? "All approvals green — ready to merge."
            : `Blocked on: ${blocked.join(", ") || "validation"}`}
        </p>
        <button
          type="button"
          data-testid={`changeset-merge-${changeset.id}`}
          disabled={!ready}
          onClick={() => onMerge?.(changeset)}
          className="rounded-md border bg-background px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
        >
          Merge changeset
        </button>
      </div>
    </section>
  );
}

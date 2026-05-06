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
  approved: "border-emerald-200 bg-emerald-50 text-emerald-700",
  rejected: "border-rose-200 bg-rose-50 text-rose-700",
  changes_requested: "border-amber-200 bg-amber-50 text-amber-700",
  pending: "border-slate-200 bg-slate-50 text-slate-600",
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
      className="rounded-md border border-slate-200 bg-white p-4 space-y-3"
    >
      <header className="space-y-1">
        <h3
          id={`changeset-title-${changeset.id}`}
          className="text-sm font-semibold"
        >
          {changeset.title}
        </h3>
        <p className="text-xs text-slate-500">
          By {changeset.authorDisplay} · {changeset.createdAt}
        </p>
      </header>
      {validationError ? (
        <p
          data-testid={`changeset-validation-${changeset.id}`}
          className="rounded-md border border-rose-200 bg-rose-50 p-2 text-xs text-rose-700"
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
            <p className="mt-1 truncate text-[11px] opacity-70">
              {a.evidenceRef}
            </p>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
        <p
          data-testid={`changeset-blocked-${changeset.id}`}
          className="text-xs text-slate-600"
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
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Merge changeset
        </button>
      </div>
    </section>
  );
}

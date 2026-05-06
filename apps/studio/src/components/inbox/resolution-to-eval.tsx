"use client";

import { useState } from "react";

import {
  DEFAULT_RESOLUTION,
  type EvalCaseFromResolution,
  type EvidenceContext,
  type ResolutionDraft,
  buildEvalCaseFromResolution,
} from "@/lib/inbox-resolution";

export type SaveEvalFn = (
  draft: EvalCaseFromResolution,
) => Promise<{ ok: boolean; error?: string; suite_id?: string }>;

export interface ResolutionToEvalProps {
  ctx: EvidenceContext;
  onSave: SaveEvalFn;
  initialDraft?: ResolutionDraft;
}

/**
 * One-click eval-case creation from an operator resolution.
 * Canonical §21.3 + §15.1.
 */
export function ResolutionToEval({
  ctx,
  onSave,
  initialDraft = DEFAULT_RESOLUTION,
}: ResolutionToEvalProps) {
  const [draft, setDraft] = useState<ResolutionDraft>(initialDraft);
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [savedSuiteId, setSavedSuiteId] = useState<string | null>(null);

  async function handleSave() {
    if (busy) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      const eval_case = buildEvalCaseFromResolution(ctx, {
        ...draft,
        saveAsEval: true,
      });
      const res = await onSave(eval_case);
      if (res.ok) {
        setSavedSuiteId(res.suite_id ?? "operator-resolutions");
      } else {
        setErrorMsg(res.error ?? "Could not save eval case");
      }
    } catch (e) {
      setErrorMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (savedSuiteId) {
    return (
      <section
        className="rounded-lg border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-900"
        data-testid="resolution-to-eval-saved"
      >
        <p className="font-medium">Saved as eval case · suite {savedSuiteId}</p>
        <p className="mt-1 text-xs">
          Linked trace <span className="font-mono">{ctx.resolutionEvidenceRef}</span> with
          tool and retrieval evidence attached. Audit trail recorded.
        </p>
      </section>
    );
  }

  return (
    <section
      className="space-y-3 rounded-lg border bg-white p-3 text-sm"
      data-testid="resolution-to-eval"
      aria-label="Save resolution as eval case"
    >
      <header>
        <h3 className="text-sm font-semibold">Save resolution as eval case</h3>
        <p className="text-xs text-zinc-500">
          One click promotes this human resolution into the eval suite. The
          trace, tool evidence, and retrieval chunks are attached automatically.
        </p>
      </header>

      <label className="block text-xs">
        <span className="font-medium text-zinc-700">Expected outcome</span>
        <textarea
          className="mt-1 w-full rounded border px-2 py-1 text-sm"
          data-testid="resolution-expected"
          rows={3}
          value={draft.expectedOutcome}
          onChange={(e) =>
            setDraft((d) => ({ ...d, expectedOutcome: e.target.value }))
          }
        />
      </label>

      <label className="block text-xs">
        <span className="font-medium text-zinc-700">Failure reason</span>
        <input
          className="mt-1 w-full rounded border px-2 py-1 text-sm"
          data-testid="resolution-failure-reason"
          value={draft.failureReason}
          onChange={(e) =>
            setDraft((d) => ({ ...d, failureReason: e.target.value }))
          }
        />
      </label>

      <ul className="rounded border bg-zinc-50 p-2 text-xs" data-testid="resolution-attachments">
        <li>
          Linked trace: <span className="font-mono">{ctx.resolutionEvidenceRef}</span>
        </li>
        <li>Tools: {ctx.tools.length}</li>
        <li>Retrieval chunks: {ctx.retrieval.length}</li>
      </ul>

      {errorMsg ? (
        <p
          className="rounded border border-red-300 bg-red-50 px-2 py-1 text-xs text-red-700"
          data-testid="resolution-to-eval-error"
          role="alert"
        >
          {errorMsg}
        </p>
      ) : null}

      <div className="flex justify-end">
        <button
          type="button"
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          data-testid="resolution-save-eval"
          disabled={
            busy ||
            draft.expectedOutcome.trim().length === 0 ||
            draft.failureReason.trim().length === 0
          }
          onClick={handleSave}
        >
          {busy ? "Saving…" : "Save as eval case"}
        </button>
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";

import {
  isThreadStale,
  resolveThreadAsEval,
  type CommentThread,
  type ResolveAsEvalInput,
} from "@/lib/comments";

interface CommentThreadViewProps {
  thread: CommentThread;
  /** Caller (e.g. cp-api adapter) that records the resolution. */
  onResolveAsEval?(input: ResolveAsEvalInput): void;
  /** Identity of the current user; used as resolvedBy. */
  currentUser: { id: string; display: string };
}

export function CommentThreadView(props: CommentThreadViewProps): JSX.Element {
  const { thread, onResolveAsEval, currentUser } = props;
  const [evalSpecId, setEvalSpecId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [localThread, setLocalThread] = useState<CommentThread>(thread);

  const stale = isThreadStale(localThread);
  const resolved = !!localThread.resolution;

  function handleResolve(): void {
    if (!evalSpecId.trim()) {
      setError("Eval spec id is required.");
      return;
    }
    setError(null);
    const input: ResolveAsEvalInput = {
      threadId: localThread.id,
      evalSpecId: evalSpecId.trim(),
      resolvedBy: currentUser.id,
      resolvedAt: new Date().toISOString(),
      evidenceRef: `audit/comments/${localThread.id}/resolve`,
    };
    try {
      const next = resolveThreadAsEval(localThread, input);
      setLocalThread(next);
      onResolveAsEval?.(input);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve.");
    }
  }

  return (
    <section
      data-testid={`comment-thread-${localThread.id}`}
      className="rounded-md border border-slate-200 bg-white p-4 space-y-3"
      aria-labelledby={`thread-title-${localThread.id}`}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3
            id={`thread-title-${localThread.id}`}
            className="text-sm font-semibold"
          >
            Thread on {localThread.anchor.kind} ·{" "}
            <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">
              {localThread.anchor.objectId}
            </code>
          </h3>
          <p className="text-xs text-slate-500">
            Authored against {localThread.anchor.authoredAt} · observed{" "}
            {localThread.observedAt}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {stale ? (
            <span
              data-testid={`thread-stale-${localThread.id}`}
              className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700"
            >
              Stale anchor
            </span>
          ) : (
            <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
              Anchored
            </span>
          )}
          {resolved ? (
            <span
              data-testid={`thread-resolved-${localThread.id}`}
              className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-medium text-sky-700"
            >
              Resolved → {localThread.resolution?.evalSpecId ?? localThread.resolution?.kind}
            </span>
          ) : null}
        </div>
      </header>
      <ul className="space-y-2">
        {localThread.comments.map((c) => (
          <li
            key={c.id}
            data-testid={`comment-${c.id}`}
            className="rounded-md border border-slate-200 bg-slate-50 p-3 text-xs"
          >
            <p className="text-sm text-slate-800">{c.body}</p>
            <p className="mt-1 text-[11px] text-slate-500">
              {c.authorDisplay} · {c.createdAt}
            </p>
          </li>
        ))}
      </ul>
      {!resolved ? (
        <div className="space-y-2 rounded-md border border-dashed border-slate-300 p-3">
          <p className="text-xs font-medium text-slate-700">
            Resolve into eval spec
          </p>
          <input
            type="text"
            data-testid={`thread-eval-input-${localThread.id}`}
            value={evalSpecId}
            onChange={(e) => setEvalSpecId(e.target.value)}
            placeholder="eval_refund_callback_over_200"
            className="w-full rounded-md border border-slate-300 px-2 py-1 text-xs"
          />
          {error ? (
            <p
              data-testid={`thread-error-${localThread.id}`}
              className="text-xs text-rose-700"
            >
              {error}
            </p>
          ) : null}
          <button
            type="button"
            data-testid={`thread-resolve-btn-${localThread.id}`}
            onClick={handleResolve}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium hover:bg-slate-50"
          >
            Resolve as eval spec
          </button>
        </div>
      ) : null}
    </section>
  );
}

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
  const [alsoCreateEval, setAlsoCreateEval] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [localThread, setLocalThread] = useState<CommentThread>(thread);

  const stale = isThreadStale(localThread);
  const resolved = !!localThread.resolution;

  function handleResolve(): void {
    if (alsoCreateEval && !evalSpecId.trim()) {
      setError("Eval spec id is required.");
      return;
    }
    setError(null);
    const input: ResolveAsEvalInput = {
      threadId: localThread.id,
      evalSpecId: alsoCreateEval ? evalSpecId.trim() : "comment-resolved",
      resolvedBy: currentUser.id,
      resolvedAt: new Date().toISOString(),
      evidenceRef: `audit/comments/${localThread.id}/resolve`,
    };
    try {
      const next = resolveThreadAsEval(localThread, input);
      setLocalThread(next);
      if (alsoCreateEval) onResolveAsEval?.(input);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to resolve.");
    }
  }

  return (
    <section
      data-testid={`comment-thread-${localThread.id}`}
      className="space-y-3 rounded-md border bg-card p-4"
      aria-labelledby={`thread-title-${localThread.id}`}
    >
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3
            id={`thread-title-${localThread.id}`}
            className="text-sm font-semibold"
          >
            Thread on {localThread.anchor.kind} ·{" "}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              {localThread.anchor.objectId}
            </code>
          </h3>
          <p className="text-xs text-muted-foreground">
            Authored against {localThread.anchor.authoredAt} · observed{" "}
            {localThread.observedAt}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {stale ? (
            <span
              data-testid={`thread-stale-${localThread.id}`}
              className="rounded-full border border-warning/40 bg-warning/10 px-2 py-0.5 text-[11px] font-medium text-warning"
            >
              Stale anchor
            </span>
          ) : (
            <span className="rounded-full border border-success/40 bg-success/10 px-2 py-0.5 text-[11px] font-medium text-success">
              Anchored
            </span>
          )}
          {resolved ? (
            <span
              data-testid={`thread-resolved-${localThread.id}`}
              className="rounded-full border border-info/40 bg-info/10 px-2 py-0.5 text-[11px] font-medium text-info"
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
            className="rounded-md border bg-background p-3 text-xs"
          >
            <p className="text-sm text-foreground">{c.body}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {c.authorDisplay} · {c.createdAt}
            </p>
          </li>
        ))}
      </ul>
      {!resolved ? (
        <div className="space-y-2 rounded-md border border-dashed p-3">
          <p className="text-xs font-medium text-foreground">
            Resolve into eval spec
          </p>
          <input
            type="text"
            data-testid={`thread-eval-input-${localThread.id}`}
            value={evalSpecId}
            onChange={(e) => setEvalSpecId(e.target.value)}
            placeholder="eval_refund_callback_over_200"
            disabled={!alsoCreateEval}
            className="w-full rounded-md border bg-background px-2 py-1 text-xs"
          />
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={alsoCreateEval}
              onChange={(e) => setAlsoCreateEval(e.target.checked)}
              data-testid={`thread-create-eval-${localThread.id}`}
            />
            Also create eval case from this resolution
          </label>
          {error ? (
            <p
              data-testid={`thread-error-${localThread.id}`}
              className="text-xs text-destructive"
            >
              {error}
            </p>
          ) : null}
          <button
            type="button"
            data-testid={`thread-resolve-btn-${localThread.id}`}
            onClick={handleResolve}
            className="rounded-md border bg-background px-2 py-1 text-xs font-medium hover:bg-muted"
          >
            {alsoCreateEval ? "Resolve as eval spec" : "Resolve comment"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

"use client";

import { useEffect, useMemo } from "react";

import type { AgentVersionDetail } from "@/lib/agent-versions";
import { diffLines, diffStats } from "@/lib/diff";

export interface DiffViewerModalProps {
  version: AgentVersionDetail;
  /** Prior version to diff against; null for the initial version. */
  prior: AgentVersionDetail | null;
  onClose: () => void;
}

/**
 * Modal showing a unified line diff of ``config_json`` between a
 * version and its predecessor. When ``prior`` is null we render the
 * full config as additions so reviewers see everything that landed in
 * the first deploy.
 */
export function DiffViewerModal({
  version,
  prior,
  onClose,
}: DiffViewerModalProps) {
  const lines = useMemo(() => {
    const oldText = prior?.config_json ?? "";
    return diffLines(oldText, version.config_json);
  }, [version, prior]);
  const { added, removed } = diffStats(lines);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Diff for v${version.version}`}
      data-testid="diff-viewer-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
    >
      <div className="flex w-full max-w-3xl flex-col gap-3 rounded-lg bg-background p-6 shadow-lg">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-lg font-semibold">
            v{version.version}
            {prior ? (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                vs v{prior.version}
              </span>
            ) : (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                (initial version)
              </span>
            )}
          </h2>
          <button
            type="button"
            onClick={onClose}
            data-testid="diff-viewer-close"
            className="rounded-md border px-2 py-1 text-sm"
          >
            Close
          </button>
        </div>
        <p
          className="text-xs text-muted-foreground"
          data-testid="diff-viewer-stats"
        >
          <span className="text-green-700">+{added}</span>{" "}
          <span className="text-red-700">-{removed}</span> lines
        </p>
        <pre
          data-testid="diff-viewer-body"
          className="max-h-[60vh] overflow-auto rounded-md border bg-muted/30 p-3 text-xs leading-5"
        >
          {lines.map((line, idx) => {
            const cls =
              line.op === "add"
                ? "bg-green-50 text-green-900"
                : line.op === "remove"
                ? "bg-red-50 text-red-900"
                : "text-muted-foreground";
            const sigil =
              line.op === "add" ? "+" : line.op === "remove" ? "-" : " ";
            return (
              <div
                key={idx}
                data-op={line.op}
                data-testid={`diff-line-${line.op}`}
                className={`flex gap-2 px-1 ${cls}`}
              >
                <span className="select-none w-4 text-right">{sigil}</span>
                <span className="select-none w-8 text-right opacity-60">
                  {line.oldLine ?? ""}
                </span>
                <span className="select-none w-8 text-right opacity-60">
                  {line.newLine ?? ""}
                </span>
                <span className="whitespace-pre-wrap">{line.text}</span>
              </div>
            );
          })}
        </pre>
      </div>
    </div>
  );
}

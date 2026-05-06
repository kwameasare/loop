"use client";

import { useMemo, useState } from "react";
import { Copy, Link as LinkIcon } from "lucide-react";

import {
  type QuickBranchSurface,
  QUICK_BRANCH_SURFACES,
  buildQuickBranchLink,
} from "@/lib/sharing";
import { cn } from "@/lib/utils";

export interface QuickBranchLinkProps {
  agentId: string;
  branch: string;
  /**
   * Hook for tests to capture the clipboard write without depending on
   * `navigator.clipboard`, which is not available in jsdom by default.
   */
  onCopy?: (url: string) => void;
}

const SURFACE_LABELS: Record<QuickBranchSurface, string> = {
  summary: "Change summary",
  "behavior-diff": "Semantic behavior diff",
  "eval-status": "Eval status",
  "preflight-blockers": "Preflight blockers",
  canary: "Canary slider",
  actions: "Approve / comment",
};

export function QuickBranchLink({
  agentId,
  branch,
  onCopy,
}: QuickBranchLinkProps) {
  const [enabled, setEnabled] = useState<Record<QuickBranchSurface, boolean>>(
    () =>
      Object.fromEntries(
        QUICK_BRANCH_SURFACES.map((key) => [key, true]),
      ) as Record<QuickBranchSurface, boolean>,
  );
  const [copied, setCopied] = useState(false);

  const url = useMemo(
    () => buildQuickBranchLink({ agentId, branch, surfaces: enabled }),
    [agentId, branch, enabled],
  );

  function toggle(surface: QuickBranchSurface) {
    setEnabled((current) => ({ ...current, [surface]: !current[surface] }));
    setCopied(false);
  }

  async function copy() {
    onCopy?.(url);
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(url);
      } catch {
        /* noop: tests rely on `onCopy` */
      }
    }
    setCopied(true);
  }

  return (
    <section
      aria-labelledby="quick-branch-title"
      className="space-y-3 rounded-md border bg-card p-3"
      data-testid="quick-branch-link"
    >
      <header>
        <h3
          id="quick-branch-title"
          className="flex items-center gap-2 text-sm font-medium"
        >
          <LinkIcon className="h-4 w-4" aria-hidden={true} />
          Quick branch review link
        </h3>
        <p className="text-xs text-muted-foreground">
          Slack-friendly URL that opens the smallest useful review surface for{" "}
          <strong>{branch}</strong>.
        </p>
      </header>
      <ul role="list" className="grid gap-1 sm:grid-cols-2">
        {QUICK_BRANCH_SURFACES.map((surface) => {
          const isOn = enabled[surface];
          return (
            <li key={surface}>
              <button
                type="button"
                role="switch"
                aria-checked={isOn}
                onClick={() => toggle(surface)}
                className={cn(
                  "flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm",
                  isOn ? "border-ring bg-accent/40" : "border-border",
                )}
                data-testid={`quick-branch-toggle-${surface}`}
              >
                <span>{SURFACE_LABELS[surface]}</span>
                <span className="text-[0.68rem] uppercase tracking-wide text-muted-foreground">
                  {isOn ? "Shown" : "Hidden"}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-2 py-1">
        <code
          className="flex-1 truncate text-xs"
          data-testid="quick-branch-url"
          title={url}
        >
          {url}
        </code>
        <button
          type="button"
          onClick={copy}
          className="inline-flex h-7 items-center gap-1 rounded-md bg-foreground/90 px-2 text-xs font-medium text-background transition-opacity duration-swift ease-standard hover:opacity-90"
          data-testid="quick-branch-copy"
        >
          <Copy className="h-3 w-3" aria-hidden={true} />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </section>
  );
}

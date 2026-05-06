"use client";

import { useMemo, useState } from "react";
import { Eye, EyeOff, Link2, ShieldCheck, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  type AccessLog,
  REDACTION_CATEGORIES,
  REDACTION_LABELS,
  type RedactionCategory,
  SHAREABLE_ARTIFACTS,
  SHARE_SCOPES,
  type ShareArtifact,
  type ShareLink,
  type ShareScope,
  buildShareLink,
  previewRedaction,
  recordAccess,
  revokeShareLink,
} from "@/lib/sharing";
import { cn } from "@/lib/utils";

export interface ShareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  artifact: ShareArtifact;
  artifactId: string;
  /** Raw payload used to render the redaction preview. */
  samplePayload: string;
  initialScope?: ShareScope;
  initialExpiresAt?: string;
  initialRedactions?: RedactionCategory[];
  /**
   * Optional clock for tests so generated ids/timestamps are deterministic.
   */
  now?: () => Date;
}

const SCOPE_LABELS: Record<ShareScope, string> = {
  workspace: "Workspace members",
  "named-people": "Named people",
  "link-anyone": "Anyone with the link",
  "branch-reviewers": "Branch reviewers",
};

export function ShareDialog({
  open,
  onOpenChange,
  artifact,
  artifactId,
  samplePayload,
  initialScope = "workspace",
  initialExpiresAt,
  initialRedactions = ["pii", "secrets"],
  now,
}: ShareDialogProps) {
  const [scope, setScope] = useState<ShareScope>(initialScope);
  const [expiresAt, setExpiresAt] = useState<string>(
    initialExpiresAt ?? defaultExpiry(now),
  );
  const [redactions, setRedactions] = useState<RedactionCategory[]>([
    ...initialRedactions,
  ]);
  const [link, setLink] = useState<ShareLink | null>(null);
  const [accessLog, setAccessLog] = useState<AccessLog>({ events: [] });

  const preview = useMemo(
    () => previewRedaction(samplePayload, { categories: redactions }),
    [samplePayload, redactions],
  );

  function toggleRedaction(category: RedactionCategory) {
    setRedactions((current) =>
      current.includes(category)
        ? current.filter((value) => value !== category)
        : [...current, category],
    );
  }

  function generate() {
    const next = buildShareLink(
      {
        artifact,
        artifactId,
        scope,
        expiresAt,
        redactions: { categories: redactions },
      },
      now,
    );
    setLink(next);
    setAccessLog(
      recordAccess(next, "you", "viewed", { events: [] }, now),
    );
  }

  function revoke() {
    if (!link) return;
    const result = revokeShareLink(link, "you", accessLog, now);
    setLink(result.link);
    setAccessLog(result.log);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl gap-4"
        data-testid="share-dialog"
      >
        <DialogHeader>
          <DialogTitle>Share {ARTIFACT_LABELS[artifact]}</DialogTitle>
          <DialogDescription>
            Recipients always see what was redacted. Every open is logged and
            you can revoke access at any time.
          </DialogDescription>
        </DialogHeader>

        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Permission scope
          </legend>
          <div role="radiogroup" aria-label="Permission scope" className="grid gap-2 sm:grid-cols-2">
            {SHARE_SCOPES.map((value) => {
              const isActive = scope === value;
              return (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={isActive}
                  onClick={() => setScope(value)}
                  className={cn(
                    "flex items-center gap-2 rounded-md border px-3 py-2 text-left text-sm transition-colors duration-swift ease-standard",
                    isActive
                      ? "border-ring bg-accent text-accent-foreground"
                      : "hover:bg-accent/60",
                  )}
                  data-testid={`share-scope-${value}`}
                >
                  <ShieldCheck
                    className="h-4 w-4 text-muted-foreground"
                    aria-hidden={true}
                  />
                  <span>{SCOPE_LABELS[value]}</span>
                </button>
              );
            })}
          </div>
        </fieldset>

        <label className="flex flex-col gap-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Expires at
          <input
            type="datetime-local"
            value={toLocalDateTime(expiresAt)}
            onChange={(event) =>
              setExpiresAt(new Date(event.target.value).toISOString())
            }
            className="h-9 rounded-md border bg-background px-2 text-sm normal-case tracking-normal text-foreground"
            data-testid="share-expires-input"
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Redactions
          </legend>
          <ul className="grid gap-1 sm:grid-cols-2">
            {REDACTION_CATEGORIES.map((category) => {
              const isOn = redactions.includes(category);
              return (
                <li key={category}>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={isOn}
                    onClick={() => toggleRedaction(category)}
                    className={cn(
                      "flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm",
                      isOn ? "border-ring bg-accent/40" : "border-border",
                    )}
                    data-testid={`share-redaction-${category}`}
                  >
                    <span className="flex items-center gap-2">
                      {isOn ? (
                        <EyeOff className="h-4 w-4" aria-hidden={true} />
                      ) : (
                        <Eye className="h-4 w-4" aria-hidden={true} />
                      )}
                      {REDACTION_LABELS[category]}
                    </span>
                    <span className="text-[0.68rem] uppercase tracking-wide text-muted-foreground">
                      {isOn ? "Redacted" : "Visible"}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </fieldset>

        <section
          aria-label="Redaction preview"
          className="space-y-1"
        >
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Recipient preview
          </h4>
          <pre
            className="max-h-40 overflow-auto whitespace-pre-wrap break-words rounded-md border bg-muted/40 p-3 text-xs"
            data-testid="share-preview"
          >
            {preview}
          </pre>
        </section>

        {link ? (
          <section
            aria-label="Share link"
            className="space-y-2 rounded-md border bg-card p-3"
            data-testid="share-link-result"
          >
            <header className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-medium">
                <Link2 className="h-4 w-4" aria-hidden={true} />
                {link.active ? "Active share link" : "Share link revoked"}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={revoke}
                disabled={!link.active}
                data-testid="share-revoke"
              >
                <X className="mr-1 h-3 w-3" aria-hidden={true} />
                Revoke
              </Button>
            </header>
            <code
              className="block break-all rounded bg-muted/40 px-2 py-1 text-xs"
              data-testid="share-url"
            >
              {link.url}
            </code>
            <details>
              <summary className="cursor-pointer text-xs text-muted-foreground">
                Access log ({accessLog.events.length})
              </summary>
              <ul className="mt-1 space-y-1 text-xs" data-testid="share-access-log">
                {accessLog.events.map((event) => (
                  <li key={event.id}>
                    <span className="font-mono">{event.outcome}</span> ·{" "}
                    {event.actor} · {event.occurredAt}
                  </li>
                ))}
              </ul>
            </details>
          </section>
        ) : null}

        <footer className="flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            Shareable as: {SHAREABLE_ARTIFACTS.length} canonical artifact types
          </span>
          <Button type="button" onClick={generate} data-testid="share-generate">
            Generate link
          </Button>
        </footer>
      </DialogContent>
    </Dialog>
  );
}

const ARTIFACT_LABELS: Record<ShareArtifact, string> = {
  trace: "trace",
  conversation: "conversation",
  "eval-result": "eval result",
  "deploy-diff": "deploy diff",
  "parity-report": "parity report",
  "cost-chart": "cost chart",
  "audit-evidence": "audit evidence",
  branch: "branch review",
};

function toLocalDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function defaultExpiry(now?: () => Date): string {
  const base = now ? now() : new Date();
  const expires = new Date(base.getTime() + 7 * 24 * 60 * 60 * 1000);
  return expires.toISOString();
}

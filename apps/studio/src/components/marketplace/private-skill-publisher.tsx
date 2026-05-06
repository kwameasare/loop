"use client";

import { useId, useMemo, useState } from "react";

import {
  MARKETPLACE_PERMISSIONS,
  type MarketplacePermission,
  type SubmissionResult,
  submitPrivateSkill,
} from "@/lib/marketplace";
import { cn } from "@/lib/utils";

export interface PrivateSkillPublisherProps {
  itemId: string;
  defaultName?: string;
  className?: string;
  onSubmit?: (result: SubmissionResult, payload: {
    itemId: string;
    version: string;
    changelog: string;
    permissions: MarketplacePermission[];
    reviewers: string[];
  }) => void;
}

export function PrivateSkillPublisher({
  itemId,
  defaultName,
  className,
  onSubmit,
}: PrivateSkillPublisherProps) {
  const formId = useId();
  const [version, setVersion] = useState("0.1.0");
  const [changelog, setChangelog] = useState("");
  const [permissions, setPermissions] = useState<MarketplacePermission[]>([]);
  const [reviewersText, setReviewersText] = useState("");
  const [result, setResult] = useState<SubmissionResult | null>(null);

  const reviewers = useMemo(
    () =>
      reviewersText
        .split(/[\s,]+/)
        .map((r) => r.trim())
        .filter(Boolean),
    [reviewersText],
  );

  const togglePermission = (p: MarketplacePermission) => {
    setPermissions((cur) =>
      cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p],
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload = { itemId, version, changelog, permissions, reviewers };
    const r = submitPrivateSkill(payload);
    setResult(r);
    onSubmit?.(r, payload);
  };

  return (
    <form
      id={formId}
      className={cn("flex flex-col gap-4 rounded-md border border-border bg-card p-5", className)}
      data-testid="private-skill-publisher"
      onSubmit={handleSubmit}
      aria-label={`Publish private skill${defaultName ? `: ${defaultName}` : ""}`}
    >
      <header>
        <h2 className="text-base font-semibold">Publish to private library</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Versioned, deprecation-aware, and review-gated. Workspace usage
          analytics start once the version is published.
        </p>
      </header>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Version</span>
        <input
          type="text"
          inputMode="text"
          required
          pattern="\d+\.\d+\.\d+"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
          className="h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
          data-testid="publisher-version"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Changelog</span>
        <textarea
          value={changelog}
          onChange={(e) => setChangelog(e.target.value)}
          rows={3}
          className="rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
          placeholder="What changed and why? Reviewers will see this."
          data-testid="publisher-changelog"
        />
      </label>

      <fieldset className="flex flex-col gap-2 text-sm">
        <legend className="font-medium">Required permissions</legend>
        <p className="text-xs text-muted-foreground">
          Sensitive permissions (money-movement, write-secrets, deploy-production)
          require two reviewers.
        </p>
        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
          {MARKETPLACE_PERMISSIONS.map((p) => (
            <li key={p}>
              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={permissions.includes(p)}
                  onChange={() => togglePermission(p)}
                  data-testid={`publisher-permission-${p}`}
                />
                {p}
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">Reviewers</span>
        <input
          type="text"
          value={reviewersText}
          onChange={(e) => setReviewersText(e.target.value)}
          placeholder="comma-separated emails"
          className="h-9 rounded-md border border-border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
          data-testid="publisher-reviewers"
        />
      </label>

      <button
        type="submit"
        className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        data-testid="publisher-submit"
      >
        Submit for review
      </button>

      {result ? (
        <div
          role="status"
          aria-live="polite"
          className={cn(
            "rounded-md border px-3 py-2 text-xs",
            result.ok
              ? "border-success bg-success/10 text-success"
              : "border-destructive bg-destructive/10 text-destructive",
          )}
          data-testid="publisher-result"
        >
          {result.ok ? (
            <p>Submitted to review queue. Lifecycle: {result.lifecycle}.</p>
          ) : (
            <ul className="flex flex-col gap-0.5">
              {result.errors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </form>
  );
}

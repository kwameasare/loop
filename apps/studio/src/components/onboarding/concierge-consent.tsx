"use client";

import { useState } from "react";
import { ShieldCheck, Undo2 } from "lucide-react";

import {
  type ConciergeRequest,
  type ConciergeResult,
  type ConciergeScope,
  ConciergeConsentError,
  runConcierge,
} from "@/lib/onboarding";
import { cn } from "@/lib/utils";

const SCOPE_LABELS: Record<ConciergeScope, string> = {
  transcripts: "Conversation transcripts",
  "tool-calls": "Tool calls and arguments",
  "kb-citations": "KB citations and retrieval evidence",
  "user-feedback": "User feedback (thumbs and notes)",
};

const ALL_SCOPES: ConciergeScope[] = [
  "transcripts",
  "tool-calls",
  "kb-citations",
  "user-feedback",
];

export interface ConciergeConsentPanelProps {
  className?: string;
  reviewer: string;
  onAccept?: (result: ConciergeResult) => void;
  onRevoke?: () => void;
  /** Inject a clock for tests/storybook. */
  now?: () => string;
}

export function ConciergeConsentPanel({
  className,
  reviewer,
  onAccept,
  onRevoke,
  now = () => new Date().toISOString(),
}: ConciergeConsentPanelProps) {
  const [scopes, setScopes] = useState<ConciergeScope[]>([
    "transcripts",
  ]);
  const [count, setCount] = useState(20);
  const [result, setResult] = useState<ConciergeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggleScope = (scope: ConciergeScope) => {
    setScopes((cur) =>
      cur.includes(scope) ? cur.filter((s) => s !== scope) : [...cur, scope],
    );
  };

  const handleAccept = () => {
    setError(null);
    const req: ConciergeRequest = {
      scopes,
      conversationsRequested: count,
      reviewer,
      consentAcceptedAt: now(),
    };
    try {
      const res = runConcierge(req);
      setResult(res);
      onAccept?.(res);
    } catch (e) {
      if (e instanceof ConciergeConsentError) setError(e.message);
      else throw e;
    }
  };

  const handleRevoke = () => {
    setResult(null);
    onRevoke?.();
  };

  if (result) {
    return (
      <section
        aria-label="Concierge results"
        data-testid="concierge-result"
        className={cn(
          "flex flex-col gap-3 rounded-md border border-border bg-card p-4",
          className,
        )}
      >
        <header className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Concierge findings</h3>
          <button
            type="button"
            onClick={handleRevoke}
            className="flex items-center gap-1 rounded-md border border-border px-3 py-1 text-xs text-muted-foreground hover:border-warning focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            data-testid="concierge-revoke"
          >
            <Undo2 aria-hidden="true" className="h-3 w-3" />
            Revoke and forget
          </button>
        </header>
        <p className="text-xs text-muted-foreground">
          Read {result.consent.conversationsRequested} conversations with scopes:{" "}
          {result.consent.scopes.join(", ")}. Accepted at{" "}
          {result.consent.acceptedAt} by {result.consent.reviewer}.
        </p>
        <dl className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
          <Group title="Starter evals" items={result.recommendations.starterEvalIds} testid="concierge-evals" />
          <Group title="Likely KB holes" items={result.recommendations.kbHoles} testid="concierge-kb" />
          <Group title="Drafted scenes" items={result.recommendations.scenes} testid="concierge-scenes" />
          <Group title="Risky tools" items={result.recommendations.riskyTools} testid="concierge-tools" />
        </dl>
        <p
          className="rounded-md border border-focus/40 bg-focus/5 p-3 text-xs"
          data-testid="concierge-improvement"
        >
          <span className="font-medium">Safe first improvement:</span>{" "}
          {result.recommendations.safeFirstImprovement}
        </p>
      </section>
    );
  }

  return (
    <section
      aria-label="Concierge consent"
      data-testid="concierge-consent"
      className={cn(
        "flex flex-col gap-3 rounded-md border border-border bg-card p-4",
        className,
      )}
    >
      <header className="flex items-start gap-2">
        <ShieldCheck aria-hidden="true" className="mt-0.5 h-4 w-4 text-focus" />
        <div>
          <h3 className="text-sm font-semibold">
            Want me to learn from your last 20 conversations?
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Studio reads only the data you check below, then suggests starter
            evals, flags KB holes, drafts scenes, identifies risky tools, and
            recommends one safe first improvement. You can revoke and forget
            at any time.
          </p>
        </div>
      </header>
      <fieldset
        className="flex flex-col gap-2"
        data-testid="concierge-scopes"
      >
        <legend className="text-xs font-medium">Data scopes</legend>
        {ALL_SCOPES.map((scope) => (
          <label key={scope} className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={scopes.includes(scope)}
              onChange={() => toggleScope(scope)}
              data-testid={`concierge-scope-${scope}`}
            />
            <span>{SCOPE_LABELS[scope]}</span>
          </label>
        ))}
      </fieldset>
      <label className="flex items-center gap-2 text-xs">
        <span>Sample size (5–50)</span>
        <input
          type="number"
          min={5}
          max={50}
          value={count}
          onChange={(e) => setCount(Number(e.target.value) || 0)}
          className="h-7 w-20 rounded-md border border-border bg-background px-2 text-xs"
          data-testid="concierge-count"
        />
      </label>
      {error ? (
        <p
          role="alert"
          data-testid="concierge-error"
          className="rounded-md border border-warning/60 bg-warning/10 p-2 text-xs text-warning"
        >
          {error}
        </p>
      ) : null}
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={handleAccept}
          className="rounded-md border border-focus bg-focus/10 px-3 py-1 text-xs font-medium text-focus hover:bg-focus/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          data-testid="concierge-accept"
        >
          Yes, learn with these scopes
        </button>
      </div>
    </section>
  );
}

interface GroupProps {
  title: string;
  items: string[];
  testid: string;
}

function Group({ title, items, testid }: GroupProps) {
  return (
    <div data-testid={testid}>
      <dt className="font-medium">{title}</dt>
      <dd>
        <ul className="mt-1 list-disc pl-4 text-muted-foreground">
          {items.map((it) => (
            <li key={it}>{it}</li>
          ))}
        </ul>
      </dd>
    </div>
  );
}

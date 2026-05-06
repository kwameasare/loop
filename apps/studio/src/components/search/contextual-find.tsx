"use client";

import { useMemo, useState } from "react";
import { Search } from "lucide-react";

import {
  type FindCandidate,
  type FindScope,
  FIND_SCOPES,
  findInContext,
} from "@/lib/search";
import { cn } from "@/lib/utils";

export interface ContextualFindProps {
  candidates: FindCandidate[];
  /** Initial scope; defaults to `workbench`. */
  scope?: FindScope;
  /** Optional handler when the user activates a result. */
  onSelect?: (result: FindCandidate) => void;
}

const SCOPE_LABELS: Record<FindScope, string> = {
  workbench: "Workbench",
  trace: "Current trace",
  audit: "Audit log",
  eval: "Eval result",
  migration: "Migration inventory",
};

export function ContextualFind({
  candidates,
  scope: initialScope = "workbench",
  onSelect,
}: ContextualFindProps) {
  const [scope, setScope] = useState<FindScope>(initialScope);
  const [query, setQuery] = useState("");

  const results = useMemo(
    () => findInContext(query, candidates, scope),
    [query, candidates, scope],
  );

  return (
    <section
      aria-label="Contextual find"
      className="space-y-3 rounded-md border bg-card p-3"
      data-testid="contextual-find"
    >
      <div className="flex items-center gap-2">
        <Search className="h-4 w-4 text-muted-foreground" aria-hidden={true} />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Find within ${SCOPE_LABELS[scope].toLowerCase()}`}
          aria-label="Find query"
          className="h-8 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          data-testid="find-input"
        />
      </div>
      <div
        role="tablist"
        aria-label="Find scope"
        className="flex flex-wrap gap-1"
      >
        {FIND_SCOPES.map((value) => {
          const isActive = scope === value;
          return (
            <button
              key={value}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setScope(value)}
              className={cn(
                "rounded-sm px-2 py-1 text-[0.7rem] uppercase tracking-wide transition-colors duration-swift ease-standard",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              data-testid={`find-scope-${value}`}
            >
              {SCOPE_LABELS[value]}
            </button>
          );
        })}
      </div>
      {results.length === 0 ? (
        <p
          role="status"
          className="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground"
          data-testid="find-empty"
        >
          Nothing matches in {SCOPE_LABELS[scope]}. Try a different scope or
          remove characters from the query.
        </p>
      ) : (
        <ul
          role="listbox"
          aria-label="Find results"
          className="space-y-1"
          data-testid="find-results"
        >
          {results.map((result) => (
            <li key={result.id}>
              <button
                type="button"
                onClick={() => onSelect?.(result)}
                className="flex w-full flex-col items-start gap-0.5 rounded-md px-3 py-2 text-left transition-colors duration-swift ease-standard hover:bg-accent/70"
                data-testid={`find-result-${result.id}`}
              >
                <span className="text-sm font-medium">{result.title}</span>
                <span className="text-xs text-muted-foreground">
                  {result.summary}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

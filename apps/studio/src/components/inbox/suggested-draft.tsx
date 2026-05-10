"use client";

import { useState } from "react";

export interface SuggestedDraftProps {
  draft: string;
  /** Called when the operator clicks "Insert" with the suggested text. */
  onInsert: (text: string) => void;
  /** Optional dismiss callback so the operator can mark the suggestion unhelpful. */
  onDismiss?: (text: string) => void;
}

/**
 * Surfaced agent-generated draft the operator can paste into the
 * composer. Canonical §21.2 "Operator sees: ... suggested draft".
 */
export function SuggestedDraft({ draft, onInsert, onDismiss }: SuggestedDraftProps) {
  const [edited, setEdited] = useState(draft);
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) {
    return (
      <p
        className="text-xs text-muted-foreground"
        data-testid="suggested-draft-dismissed"
      >
        Suggested draft dismissed. Compose your own reply below.
      </p>
    );
  }

  return (
    <section
      className="rounded-lg border border-info/40 bg-info/10 p-3 text-sm"
      data-testid="suggested-draft"
      aria-label="Suggested operator draft"
    >
      <header className="mb-2 flex items-center justify-between text-xs">
        <span className="font-medium text-foreground">Suggested draft</span>
        <span className="rounded bg-background px-2 py-0.5 text-[11px] text-info">
          source: agent · review before sending
        </span>
      </header>
      <textarea
        className="w-full rounded border bg-background p-2 text-sm"
        data-testid="suggested-draft-text"
        rows={3}
        value={edited}
        onChange={(e) => setEdited(e.target.value)}
      />
      <div className="mt-2 flex justify-end gap-2">
        {onDismiss ? (
          <button
            type="button"
            className="rounded border bg-background px-3 py-1 text-xs text-foreground hover:bg-muted"
            data-testid="suggested-draft-dismiss"
            onClick={() => {
              onDismiss(edited);
              setDismissed(true);
            }}
          >
            Dismiss
          </button>
        ) : null}
        <button
          type="button"
          className="rounded bg-primary px-3 py-1 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          data-testid="suggested-draft-insert"
          onClick={() => onInsert(edited)}
        >
          Insert into composer
        </button>
      </div>
    </section>
  );
}

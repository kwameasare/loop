"use client";

/**
 * P0.3: "New suite" modal launched from /evals.
 *
 * Pure client form so it can validate uniqueness before round-tripping
 * cp-api. The page hands in the existing slug list (used to flag
 * collisions early) and a submit handler that resolves with the
 * created suite — the page refreshes in place.
 */

import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { createEvalSuite } from "@/lib/evals";

const SLUG_RE = /^[a-z][a-z0-9_\-]{1,63}$/;

export interface NewSuiteModalProps {
  /** Existing suite names (to surface duplicate-name errors before POST). */
  existingNames: string[];
  /** Default agent id; the input may be empty if the user has none. */
  agentIds: string[];
}

export function NewSuiteModal({ existingNames, agentIds }: NewSuiteModalProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [agentId, setAgentId] = useState(agentIds[0] ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const formId = useId();

  function reset() {
    setName("");
    setAgentId(agentIds[0] ?? "");
    setError(null);
    setSubmitting(false);
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const trimmed = name.trim();
    if (!SLUG_RE.test(trimmed)) {
      setError(
        "Name must start with a lowercase letter and contain only lowercase letters, digits, dashes or underscores.",
      );
      return;
    }
    if (existingNames.includes(trimmed)) {
      setError("A suite with this name already exists.");
      return;
    }
    if (!agentId) {
      setError("Pick the agent this suite grades.");
      return;
    }
    setSubmitting(true);
    try {
      await createEvalSuite({ name: trimmed, agentId });
      setOpen(false);
      reset();
      // The /evals page is force-dynamic, so a router refresh is the
      // canonical way to pick up the new row without losing scroll.
      if (typeof window !== "undefined") {
        window.location.reload();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create suite");
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <Button
        onClick={() => setOpen(true)}
        data-testid="new-suite-open"
        type="button"
      >
        New suite
      </Button>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-3 rounded-lg border p-4"
      data-testid="new-suite-form"
      aria-labelledby={`${formId}-title`}
    >
      <h3 id={`${formId}-title`} className="text-sm font-medium">
        New suite
      </h3>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground" htmlFor={`${formId}-name`}>
          Suite name
        </label>
        <input
          id={`${formId}-name`}
          className="rounded border border-border bg-background px-2 py-1 text-sm"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="support-smoke"
          disabled={submitting}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-muted-foreground" htmlFor={`${formId}-agent`}>
          Agent
        </label>
        <select
          id={`${formId}-agent`}
          className="rounded border border-border bg-background px-2 py-1 text-sm"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          disabled={submitting || agentIds.length === 0}
        >
          {agentIds.length === 0 ? (
            <option value="">No agents available</option>
          ) : (
            agentIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))
          )}
        </select>
      </div>
      {error ? (
        <p className="text-sm text-red-600" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" disabled={submitting} data-testid="new-suite-submit">
          {submitting ? "Creating…" : "Create"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setOpen(false);
            reset();
          }}
          disabled={submitting}
        >
          Cancel
        </Button>
      </div>
    </form>
  );
}

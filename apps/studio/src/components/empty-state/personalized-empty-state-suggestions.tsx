"use client";

import { useEffect, useState } from "react";
import { ExternalLink, Sparkles } from "lucide-react";

import { EvidenceCallout, StatePanel } from "@/components/target";
import {
  acceptEmptyStateSuggestion,
  fetchEmptyStateSuggestions,
  type EmptyStateSuggestion,
  type EmptyStateSuggestionActionResult,
  type EmptyStateSurface,
} from "@/lib/empty-state-suggestions";

export function PersonalizedEmptyStateSuggestions({
  agentId,
  surface,
  acceptSuggestion = acceptEmptyStateSuggestion,
}: {
  agentId: string;
  surface: EmptyStateSurface;
  acceptSuggestion?: typeof acceptEmptyStateSuggestion;
}) {
  const [items, setItems] = useState<EmptyStateSuggestion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [acceptingId, setAcceptingId] = useState<string | null>(null);
  const [accepted, setAccepted] =
    useState<EmptyStateSuggestionActionResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setActionError(null);
    setAccepted(null);
    setAcceptingId(null);
    setItems([]);
    void fetchEmptyStateSuggestions(agentId, surface)
      .then((next) => {
        if (!cancelled) setItems(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error
              ? err.message
              : "Could not load personalized suggestions.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, surface]);

  async function handleAccept(item: EmptyStateSuggestion) {
    setActionError(null);
    setAccepted(null);
    setAcceptingId(item.id);
    try {
      const result = await acceptSuggestion(agentId, surface, item.id);
      setAccepted(result);
    } catch (err: unknown) {
      setActionError(
        err instanceof Error ? err.message : "Could not apply suggestion.",
      );
    } finally {
      setAcceptingId(null);
    }
  }

  if (items.length === 0 && !error) return null;

  return (
    <div className="mt-3 space-y-2" data-testid={`personalized-empty-${surface}`}>
      {error ? (
        <StatePanel state="degraded" title="Personalized suggestions unavailable">
          {error}
        </StatePanel>
      ) : null}
      {actionError ? (
        <StatePanel state="error" title="Suggestion action failed">
          {actionError}
        </StatePanel>
      ) : null}
      {accepted ? (
        <StatePanel
          state="success"
          title={accepted.title}
          action={
            accepted.next_url ? (
              <a
                className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50"
                href={accepted.next_url}
              >
                Open result
                <ExternalLink className="h-4 w-4" aria-hidden />
              </a>
            ) : null
          }
        >
          <span>{accepted.created_refs.join(", ")}</span>
          <span className="mt-1 block text-xs">
            Source: {accepted.evidence_ref}
          </span>
        </StatePanel>
      ) : null}
      {items.map((item) => (
        <EvidenceCallout
          key={item.id}
          title={item.title}
          source={item.evidence_ref}
          confidence={82}
          tone="info"
        >
          {item.id === "collect_first_proof_traces" ? (
            <a
              className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50"
              href={`/agents/${encodeURIComponent(agentId)}/simulator`}
            >
              <Sparkles className="h-4 w-4" aria-hidden />
              {item.action_label}
            </a>
          ) : (
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => void handleAccept(item)}
              disabled={acceptingId === item.id}
            >
              <Sparkles className="h-4 w-4" aria-hidden />
              {acceptingId === item.id ? "Working..." : item.action_label}
            </button>
          )}
        </EvidenceCallout>
      ))}
    </div>
  );
}

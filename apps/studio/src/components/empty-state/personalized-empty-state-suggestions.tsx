"use client";

import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

import { EvidenceCallout } from "@/components/target";
import {
  fetchEmptyStateSuggestions,
  type EmptyStateSuggestion,
  type EmptyStateSurface,
} from "@/lib/empty-state-suggestions";

export function PersonalizedEmptyStateSuggestions({
  agentId,
  surface,
}: {
  agentId: string;
  surface: EmptyStateSurface;
}) {
  const [items, setItems] = useState<EmptyStateSuggestion[]>([]);

  useEffect(() => {
    let cancelled = false;
    void fetchEmptyStateSuggestions(agentId, surface).then((next) => {
      if (!cancelled) setItems(next);
    });
    return () => {
      cancelled = true;
    };
  }, [agentId, surface]);

  if (items.length === 0) return null;

  return (
    <div className="mt-3 space-y-2" data-testid={`personalized-empty-${surface}`}>
      {items.map((item) => (
        <EvidenceCallout
          key={item.id}
          title={item.title}
          source={item.evidence_ref}
          confidence={82}
          tone="info"
        >
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50"
          >
            <Sparkles className="h-4 w-4" aria-hidden />
            {item.action_label}
          </button>
        </EvidenceCallout>
      ))}
    </div>
  );
}

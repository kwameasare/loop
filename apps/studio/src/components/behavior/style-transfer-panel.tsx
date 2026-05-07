"use client";

import { useState } from "react";
import { WandSparkles } from "lucide-react";

import { DiffRibbon, LiveBadge, StatePanel } from "@/components/target";
import { cpJson } from "@/lib/ux-wireup";

export interface StyleTransferItem {
  voice: "formal" | "casual" | "empathetic" | "concise" | "expert" | string;
  rewrite: string;
  eval_delta: number;
  evidence_ref: string;
}

export function StyleTransferPanel({
  agentId,
  section,
}: {
  agentId: string;
  section: string;
}) {
  const [items, setItems] = useState<StyleTransferItem[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function tryVoices() {
    const trimmed = section.trim();
    if (!trimmed) return;
    setRunning(true);
    setError(null);
    try {
      const result = await cpJson<{ items: StyleTransferItem[] }>(
        `/agents/${encodeURIComponent(agentId)}/style-transfer`,
        {
          method: "POST",
          body: { section: trimmed },
          fallback: {
            items: ["formal", "casual", "empathetic", "concise", "expert"].map(
              (voice, index) => ({
                voice,
                rewrite: `[${voice}] ${trimmed}`,
                eval_delta: (index - 2) * 0.01,
                evidence_ref: `style-transfer/${agentId}/${voice}`,
              }),
            ),
          },
        },
      );
      setItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Style transfer failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section
      className="rounded-md border bg-card p-4"
      data-testid="style-transfer-panel"
      aria-labelledby="style-transfer-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Try voices
          </p>
          <h3 className="mt-1 text-sm font-semibold" id="style-transfer-heading">
            Same policy, different tone
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Preview formal, casual, empathetic, concise, and expert rewrites
            with eval deltas before changing behavior.
          </p>
        </div>
        <LiveBadge tone={items.length > 0 ? "staged" : "draft"}>
          {items.length || 5} voices
        </LiveBadge>
      </div>
      <button
        type="button"
        className="mt-4 inline-flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm font-medium hover:bg-muted/50 disabled:opacity-60"
        onClick={() => void tryVoices()}
        disabled={running || !section.trim()}
        data-testid="style-transfer-run"
      >
        <WandSparkles className="h-4 w-4" aria-hidden />
        {running ? "Trying voices" : "Try voices"}
      </button>

      {error ? (
        <StatePanel className="mt-4" state="error" title="Could not try voices">
          {error}
        </StatePanel>
      ) : null}

      {items.length > 0 ? (
        <div className="mt-4 space-y-3" data-testid="style-transfer-results">
          {items.map((item) => (
            <DiffRibbon
              key={item.voice}
              label={`${item.voice} voice · eval delta ${
                item.eval_delta >= 0 ? "+" : ""
              }${item.eval_delta}`}
              before={section}
              after={item.rewrite}
              impact={item.evidence_ref}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}

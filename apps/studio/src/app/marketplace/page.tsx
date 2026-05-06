"use client";

/**
 * UX403 — Marketplace surface.
 *
 * Lists tools, templates, skills, eval packs, KB connectors, and
 * channel packs with trust + permission metadata. Lets workspace
 * builders open the detail view and lets private-workspace publishers
 * stage a new skill version for review.
 *
 * The catalog is backed by `DEFAULT_MARKETPLACE_CATALOG` until the
 * marketplace control-plane endpoint lands. No live network calls.
 */

import { useState } from "react";

import {
  MarketplaceDetail,
  MarketplaceGrid,
  PrivateSkillPublisher,
} from "@/components/marketplace";
import {
  DEFAULT_MARKETPLACE_CATALOG,
  type MarketplaceItem,
} from "@/lib/marketplace";

export default function MarketplacePage(): JSX.Element {
  const [selected, setSelected] = useState<MarketplaceItem | null>(null);
  const [tab, setTab] = useState<"browse" | "publish">("browse");

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6" aria-label="Marketplace">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Marketplace</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse trusted tools, templates, skills, eval packs, KB connectors,
            and channel packs. Publish private workspace skills with versioning,
            deprecation, and review.
          </p>
        </div>
        <div role="tablist" aria-label="Marketplace mode" className="flex gap-1">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "browse"}
            onClick={() => setTab("browse")}
            className={`h-9 rounded-md border px-3 text-sm ${
              tab === "browse"
                ? "border-focus bg-focus/10 text-foreground"
                : "border-border bg-background text-muted-foreground"
            }`}
            data-testid="marketplace-tab-browse"
          >
            Browse
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "publish"}
            onClick={() => setTab("publish")}
            className={`h-9 rounded-md border px-3 text-sm ${
              tab === "publish"
                ? "border-focus bg-focus/10 text-foreground"
                : "border-border bg-background text-muted-foreground"
            }`}
            data-testid="marketplace-tab-publish"
          >
            Publish
          </button>
        </div>
      </header>

      {tab === "browse" ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_3fr]">
          <MarketplaceGrid
            items={DEFAULT_MARKETPLACE_CATALOG}
            includeDeprecated
            onSelect={setSelected}
          />
          <div>
            {selected ? (
              <MarketplaceDetail item={selected} />
            ) : (
              <p
                role="status"
                className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
              >
                Select an item to see permissions, security posture, sample evals,
                screenshots, and version history.
              </p>
            )}
          </div>
        </div>
      ) : (
        <PrivateSkillPublisher itemId="mk_skill_pii_redactor" />
      )}
    </main>
  );
}

"use client";

/**
 * UX403 — Marketplace surface.
 *
 * Lists tools, templates, skills, eval packs, KB connectors, and
 * channel packs with trust + permission metadata. Lets workspace
 * builders open the detail view and lets private-workspace publishers
 * stage a new skill version for review.
 *
 * The catalog loads from `GET /v1/marketplace`. Without cp-api, the page shows
 * an empty catalog instead of a local fixture.
 */

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/require-auth";
import {
  MarketplaceDetail,
  MarketplaceGrid,
  MarketplaceOperations,
  PrivateSkillPublisher,
} from "@/components/marketplace";
import { SectionDegraded } from "@/components/section-states";
import {
  fetchMarketplaceCatalog,
  installMarketplaceItem,
  type MarketplaceInstall,
  type MarketplaceItem,
} from "@/lib/marketplace";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

export default function MarketplacePage(): JSX.Element {
  return (
    <RequireAuth>
      <MarketplacePageBody />
    </RequireAuth>
  );
}

function MarketplacePageBody(): JSX.Element {
  const [selected, setSelected] = useState<MarketplaceItem | null>(null);
  const [tab, setTab] = useState<"browse" | "publish">("browse");
  const [items, setItems] = useState<MarketplaceItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [installStatus, setInstallStatus] = useState<MarketplaceInstall | null>(
    null,
  );
  const [installError, setInstallError] = useState<string | null>(null);
  const { active } = useActiveWorkspace();

  useEffect(() => {
    let cancelled = false;
    void fetchMarketplaceCatalog()
      .then((catalog) => {
        if (cancelled) return;
        setItems(catalog);
        setSelected((current) => current ?? catalog[0] ?? null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Could not load marketplace",
        );
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function replaceItem(next: MarketplaceItem): void {
    setItems((current) =>
      current?.map((item) => (item.id === next.id ? next : item)) ?? current,
    );
    setSelected(next);
  }

  function selectItem(item: MarketplaceItem): void {
    setSelected(item);
    setInstallStatus(null);
    setInstallError(null);
  }

  async function installItem(item: MarketplaceItem): Promise<void> {
    if (!active?.id) {
      setInstallError("Select a workspace before installing marketplace items.");
      return;
    }
    setInstallStatus(null);
    setInstallError(null);
    try {
      const install = await installMarketplaceItem(active.id, item.id);
      setInstallStatus(install);
      const updated = { ...item, installCount: item.installCount + 1 };
      replaceItem(updated);
    } catch (err) {
      setInstallError(
        err instanceof Error ? err.message : "Could not install marketplace item.",
      );
    }
  }

  return (
    <main
      className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6"
      aria-label="Marketplace"
    >
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Marketplace</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Browse trusted tools, templates, skills, eval packs, KB connectors,
            and channel packs. Publish private workspace skills with versioning,
            deprecation, and review.
          </p>
        </div>
        <div
          role="tablist"
          aria-label="Marketplace mode"
          className="flex gap-1"
        >
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
        error ? (
          <SectionDegraded
            title="Marketplace"
            description="Marketplace catalog evidence could not load from the control plane."
            evidence={error}
          />
        ) : (
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_2fr_1.2fr]">
            <MarketplaceGrid
              items={items ?? []}
              includeDeprecated
              onSelect={selectItem}
            />
            <div>
              {items === null ? (
                <p
                  role="status"
                  className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
                >
                  Loading marketplace...
                </p>
              ) : selected ? (
                <MarketplaceDetail
                  item={selected}
                  onInstall={(item) => void installItem(item)}
                />
              ) : (
                <p
                  role="status"
                  className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
                >
                  Select an item to see permissions, security posture, sample
                  evals, screenshots, and version history.
                </p>
              )}
            </div>
            {selected ? (
              <MarketplaceOperations
                item={selected}
                installStatus={installStatus}
                installError={installError}
                onItemChanged={replaceItem}
                {...(active?.id ? { workspaceId: active.id } : {})}
              />
            ) : null}
          </div>
        )
      ) : (
        <PrivateSkillPublisher
          itemId="mk_skill_pii_redactor"
          {...(active?.id ? { workspaceId: active.id } : {})}
        />
      )}
    </main>
  );
}

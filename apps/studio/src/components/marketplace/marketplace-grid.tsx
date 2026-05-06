"use client";

import { useMemo, useState } from "react";
import { Search, Star } from "lucide-react";

import { LiveBadge } from "@/components/target";
import {
  DEFAULT_MARKETPLACE_CATALOG,
  MARKETPLACE_ITEM_KIND_LABELS,
  MARKETPLACE_ITEM_KINDS,
  MARKETPLACE_PUBLISHERS,
  type MarketplaceFilter,
  type MarketplaceItem,
  type MarketplaceItemKind,
  type MarketplacePublisher,
  currentVersion,
  filterMarketplace,
  formatInstallCount,
} from "@/lib/marketplace";
import { cn } from "@/lib/utils";

export interface MarketplaceGridProps {
  items?: readonly MarketplaceItem[];
  curatedIds?: ReadonlySet<string>;
  /** When set, restricts visible items to enterprise-curated ones. */
  enterpriseCurated?: boolean;
  /** When true, deprecated items remain visible with a notice. */
  includeDeprecated?: boolean;
  onSelect?: (item: MarketplaceItem) => void;
  className?: string;
}

const PUBLISHER_LABEL: Record<MarketplacePublisher, string> = {
  official: "Official",
  "verified-partner": "Verified partner",
  community: "Community",
  "private-workspace": "Private workspace",
};

export function MarketplaceGrid({
  items = DEFAULT_MARKETPLACE_CATALOG,
  curatedIds,
  enterpriseCurated = false,
  includeDeprecated = false,
  onSelect,
  className,
}: MarketplaceGridProps) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<MarketplaceItemKind | "all">("all");
  const [publisher, setPublisher] = useState<MarketplacePublisher | "all">("all");

  const filtered = useMemo(() => {
    const filter: MarketplaceFilter = {
      query,
      kind,
      publisher,
      includeDeprecated,
      curatedOnly: enterpriseCurated,
      ...(curatedIds ? { curatedIds } : {}),
    };
    return filterMarketplace(items, filter);
  }, [items, query, kind, publisher, includeDeprecated, enterpriseCurated, curatedIds]);

  return (
    <section
      className={cn("flex flex-col gap-4", className)}
      data-testid="marketplace-grid"
      aria-label="Marketplace catalog"
    >
      <div className="flex flex-wrap items-center gap-3">
        <label className="relative flex-1 min-w-[16rem]">
          <span className="sr-only">Search marketplace</span>
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search tools, templates, skills, eval packs…"
            className="h-10 w-full rounded-md border border-border bg-background pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-focus"
            data-testid="marketplace-search"
          />
        </label>
        <label className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Kind</span>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value as MarketplaceItemKind | "all")}
            className="h-9 rounded-md border border-border bg-background px-2 text-sm"
            data-testid="marketplace-kind"
          >
            <option value="all">All</option>
            {MARKETPLACE_ITEM_KINDS.map((k) => (
              <option key={k} value={k}>
                {MARKETPLACE_ITEM_KIND_LABELS[k]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-xs">
          <span className="text-muted-foreground">Publisher</span>
          <select
            value={publisher}
            onChange={(e) =>
              setPublisher(e.target.value as MarketplacePublisher | "all")
            }
            className="h-9 rounded-md border border-border bg-background px-2 text-sm"
            data-testid="marketplace-publisher"
          >
            <option value="all">All</option>
            {MARKETPLACE_PUBLISHERS.map((p) => (
              <option key={p} value={p}>
                {PUBLISHER_LABEL[p]}
              </option>
            ))}
          </select>
        </label>
        {enterpriseCurated ? (
          <span
            className="rounded-md border border-info bg-info/10 px-2 py-1 text-xs text-info"
            data-testid="marketplace-curated-badge"
          >
            Curated by workspace admin
          </span>
        ) : null}
      </div>

      {filtered.length === 0 ? (
        <p
          role="status"
          className="rounded-md border border-dashed border-border bg-card p-6 text-center text-sm text-muted-foreground"
          data-testid="marketplace-empty"
        >
          No marketplace items match this filter yet. Try clearing the search or
          adding items to the curated list.
        </p>
      ) : (
        <ul
          className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="marketplace-list"
        >
          {filtered.map((item) => (
            <li key={item.id}>
              <MarketplaceCard
                item={item}
                {...(onSelect ? { onSelect } : {})}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface CardProps {
  item: MarketplaceItem;
  onSelect?: (item: MarketplaceItem) => void;
}

function MarketplaceCard({ item, onSelect }: CardProps) {
  const v = currentVersion(item);
  const trustTone =
    item.lifecycle === "deprecated"
      ? "paused"
      : item.trust === "verified"
        ? "live"
        : item.trust === "internal"
          ? "staged"
          : item.trust === "community"
            ? "draft"
            : "draft";
  return (
    <button
      type="button"
      onClick={() => onSelect?.(item)}
      className="group flex h-full w-full flex-col gap-3 rounded-md border border-border bg-card p-4 text-left transition-colors duration-swift ease-standard hover:border-focus focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      data-testid={`marketplace-card-${item.id}`}
      aria-label={`${item.name} — ${MARKETPLACE_ITEM_KIND_LABELS[item.kind]}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {MARKETPLACE_ITEM_KIND_LABELS[item.kind]} · {PUBLISHER_LABEL[item.publisher]}
          </p>
          <h3 className="mt-1 text-sm font-semibold">{item.name}</h3>
          <p className="mt-1 text-xs text-muted-foreground">{item.tagline}</p>
        </div>
        <LiveBadge tone={trustTone}>
          {item.lifecycle === "deprecated"
            ? "Deprecated"
            : item.lifecycle === "in-review"
              ? "In review"
              : item.trust === "verified"
                ? "Verified"
                : item.trust === "internal"
                  ? "Internal"
                  : "Unverified"}
        </LiveBadge>
      </div>

      <dl className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
        <div>
          <dt className="sr-only">Version</dt>
          <dd data-testid={`marketplace-card-version-${item.id}`}>
            v{v?.version ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="sr-only">Installs</dt>
          <dd>{formatInstallCount(item.installCount)} installs</dd>
        </div>
        <div className="flex items-center gap-1">
          <Star aria-hidden="true" className="h-3 w-3 fill-current" />
          <span>
            {item.rating.toFixed(1)} ({item.ratingCount})
          </span>
        </div>
        <div>{item.license}</div>
      </dl>

      {item.lifecycle === "deprecated" && item.deprecationNotice ? (
        <p
          className="rounded-sm border border-warning bg-warning/10 px-2 py-1 text-xs text-warning"
          data-testid={`marketplace-card-deprecation-${item.id}`}
        >
          {item.deprecationNotice}
        </p>
      ) : null}
    </button>
  );
}

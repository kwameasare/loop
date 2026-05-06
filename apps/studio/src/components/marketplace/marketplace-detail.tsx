"use client";

import { ShieldCheck, ChartBar, Lock, History, Activity, FileText } from "lucide-react";

import { LiveBadge } from "@/components/target";
import {
  MARKETPLACE_ITEM_KIND_LABELS,
  type MarketplaceItem,
  currentVersion,
  formatInstallCount,
} from "@/lib/marketplace";
import { cn } from "@/lib/utils";

export interface MarketplaceDetailProps {
  item: MarketplaceItem;
  className?: string;
  onInstall?: (item: MarketplaceItem) => void;
}

export function MarketplaceDetail({ item, className, onInstall }: MarketplaceDetailProps) {
  const live = currentVersion(item);
  const tone =
    item.lifecycle === "deprecated"
      ? "paused"
      : item.lifecycle === "in-review"
        ? "canary"
        : item.trust === "verified"
          ? "live"
          : "draft";
  return (
    <article
      className={cn("flex flex-col gap-5 rounded-md border border-border bg-card p-5", className)}
      data-testid={`marketplace-detail-${item.id}`}
    >
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">
            {MARKETPLACE_ITEM_KIND_LABELS[item.kind]} · {item.author}
          </p>
          <h2 className="mt-1 text-lg font-semibold">{item.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{item.tagline}</p>
        </div>
        <div className="flex items-center gap-2">
          <LiveBadge tone={tone}>
            {item.lifecycle === "deprecated"
              ? "Deprecated"
              : item.lifecycle === "in-review"
                ? "In review"
                : item.lifecycle === "draft"
                  ? "Draft"
                  : item.lifecycle === "archived"
                    ? "Archived"
                    : "Published"}
          </LiveBadge>
          <button
            type="button"
            onClick={() => onInstall?.(item)}
            disabled={item.lifecycle !== "published"}
            className="inline-flex h-9 items-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition-colors duration-swift ease-standard hover:bg-primary/90 disabled:opacity-50"
            data-testid={`marketplace-install-${item.id}`}
          >
            Install
          </button>
        </div>
      </header>

      {item.lifecycle === "deprecated" && item.deprecationNotice ? (
        <p
          role="status"
          className="rounded-md border border-warning bg-warning/10 px-3 py-2 text-sm text-warning"
          data-testid="marketplace-detail-deprecation"
        >
          {item.deprecationNotice}
        </p>
      ) : null}

      <p className="text-sm">{item.description}</p>

      <dl className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <Stat icon={Activity} label="Installs" value={formatInstallCount(item.installCount)} />
        <Stat
          icon={ChartBar}
          label="Rating"
          value={`${item.rating.toFixed(1)} (${item.ratingCount})`}
        />
        <Stat
          icon={FileText}
          label="License"
          value={item.license}
        />
        <Stat
          icon={Activity}
          label="Workspace 7d"
          value={
            typeof item.workspaceUsage7d === "number"
              ? `${item.workspaceUsage7d} runs`
              : "—"
          }
        />
      </dl>

      <section aria-label="Security posture" className="rounded-md border border-border p-3">
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <ShieldCheck aria-hidden="true" className="h-4 w-4" />
          Security posture
        </h3>
        <p className="mt-1 text-xs text-muted-foreground">{item.securityPosture}</p>
        <ul
          className="mt-2 flex flex-wrap gap-1.5"
          data-testid="marketplace-detail-permissions"
        >
          {item.permissions.map((p) => (
            <li
              key={p}
              className="inline-flex items-center gap-1 rounded-sm border border-border bg-muted px-2 py-0.5 text-xs"
            >
              <Lock aria-hidden="true" className="h-3 w-3" />
              {p}
            </li>
          ))}
          {item.permissions.length === 0 ? (
            <li className="text-xs text-muted-foreground">No elevated permissions required.</li>
          ) : null}
        </ul>
      </section>

      <section aria-label="Sample evals" className="rounded-md border border-border p-3">
        <h3 className="text-sm font-medium">Sample evals</h3>
        {item.sampleEvals.length === 0 ? (
          <p className="mt-1 text-xs text-muted-foreground">No sample evals shipped yet.</p>
        ) : (
          <ul
            className="mt-2 flex flex-col gap-1 text-xs"
            data-testid="marketplace-detail-evals"
          >
            {item.sampleEvals.map((ev) => (
              <li key={ev.id} className="flex items-center justify-between gap-2">
                <span>{ev.name}</span>
                <span className="text-muted-foreground">
                  {Math.round(ev.passRate * 100)}% · {ev.cases} cases
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-label="Screenshots" className="rounded-md border border-border p-3">
        <h3 className="text-sm font-medium">Screenshots</h3>
        <ul
          className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3"
          data-testid="marketplace-detail-screenshots"
        >
          {item.screenshots.map((alt) => (
            <li
              key={alt}
              className="flex h-24 items-end justify-start rounded-sm border border-dashed border-border bg-muted p-2 text-xs text-muted-foreground"
              role="img"
              aria-label={alt}
            >
              {alt}
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Version history" className="rounded-md border border-border p-3">
        <h3 className="flex items-center gap-2 text-sm font-medium">
          <History aria-hidden="true" className="h-4 w-4" />
          Version history
        </h3>
        <ul
          className="mt-2 flex flex-col gap-1 text-xs"
          data-testid="marketplace-detail-versions"
        >
          {item.versions.map((v) => (
            <li
              key={v.version}
              className={cn(
                "flex items-center justify-between gap-2",
                v.yanked && "text-muted-foreground line-through",
              )}
            >
              <span>
                v{v.version}{" "}
                {v === live ? (
                  <span className="ml-1 rounded-sm border border-success bg-success/10 px-1 text-[10px] uppercase text-success">
                    current
                  </span>
                ) : null}
              </span>
              <span className="text-muted-foreground">
                {v.releasedAt} · {v.signed ? "signed" : "unsigned"}
                {v.yanked ? " · yanked" : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}

interface StatProps {
  icon: React.ElementType;
  label: string;
  value: string;
}

function Stat({ icon: Icon, label, value }: StatProps) {
  return (
    <div className="rounded-sm border border-border bg-background p-2">
      <dt className="flex items-center gap-1 text-[10px] uppercase tracking-wide text-muted-foreground">
        <Icon aria-hidden="true" className="h-3 w-3" />
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium">{value}</dd>
    </div>
  );
}

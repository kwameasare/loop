"use client";

import { useState } from "react";
import { Bookmark, BookmarkPlus, Trash2 } from "lucide-react";

import {
  type SavedSearch,
  type SavedSearchStore,
  createSavedSearchStore,
} from "@/lib/search";
import { cn } from "@/lib/utils";

export interface SavedSearchesProps {
  /** Optional pre-built store for tests; otherwise uses defaults. */
  store?: SavedSearchStore;
  onOpen?: (search: SavedSearch) => void;
}

export function SavedSearches({ store, onOpen }: SavedSearchesProps) {
  const [internal] = useState(() => store ?? createSavedSearchStore());
  const [items, setItems] = useState<SavedSearch[]>(() => internal.list());

  function handleOpen(search: SavedSearch) {
    setItems(internal.touch(search.id));
    onOpen?.(search);
  }

  function handleRemove(id: string) {
    setItems(internal.remove(id));
  }

  return (
    <section
      aria-labelledby="saved-searches-title"
      className="space-y-2 rounded-md border bg-card p-3"
      data-testid="saved-searches"
    >
      <header className="flex items-center justify-between">
        <h3
          id="saved-searches-title"
          className="flex items-center gap-2 text-sm font-medium"
        >
          <Bookmark className="h-4 w-4" aria-hidden={true} />
          Saved searches
        </h3>
        <span className="text-[0.68rem] uppercase tracking-wide text-muted-foreground">
          {items.length} pinned
        </span>
      </header>
      {items.length === 0 ? (
        <p
          role="status"
          className="rounded-md border border-dashed px-3 py-4 text-center text-xs text-muted-foreground"
        >
          No saved searches yet. Pin a query from the find panel to keep it one
          click away.
        </p>
      ) : (
        <ul role="list" className="space-y-1">
          {items.map((search) => (
            <li
              key={search.id}
              className="flex items-center justify-between gap-2 rounded-md px-2 py-1 hover:bg-accent/40"
              data-testid={`saved-search-${search.id}`}
            >
              <button
                type="button"
                onClick={() => handleOpen(search)}
                className={cn(
                  "flex flex-1 flex-col items-start text-left",
                  search.lastUsed ? "text-foreground" : "text-foreground",
                )}
              >
                <span className="text-sm font-medium">{search.name}</span>
                <span className="text-xs text-muted-foreground">
                  {search.scope} · {search.category}
                </span>
              </button>
              <button
                type="button"
                aria-label={`Remove ${search.name}`}
                onClick={() => handleRemove(search.id)}
                className="rounded-md p-1 text-muted-foreground transition-colors duration-swift ease-standard hover:text-foreground"
                data-testid={`saved-search-remove-${search.id}`}
              >
                <Trash2 className="h-4 w-4" aria-hidden={true} />
              </button>
            </li>
          ))}
        </ul>
      )}
      <footer className="flex items-center justify-end pt-1">
        <span className="inline-flex items-center gap-1 text-[0.68rem] text-muted-foreground">
          <BookmarkPlus className="h-3 w-3" aria-hidden={true} />
          Pin from the find panel
        </span>
      </footer>
    </section>
  );
}

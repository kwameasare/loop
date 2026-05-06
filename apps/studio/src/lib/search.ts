/**
 * Find-in-context and saved-search primitives (section 27.2 and 27.3).
 *
 * These helpers stay framework-agnostic so the search drawer, command palette
 * results section, and any feature-specific find affordance can share ranking
 * and saved-search logic.
 */

/** The contexts a builder can scope a find against (section 27.2). */
export const FIND_SCOPES = [
  "workbench",
  "trace",
  "audit",
  "eval",
  "migration",
] as const;

export type FindScope = (typeof FIND_SCOPES)[number];

export interface FindCandidate {
  id: string;
  scope: FindScope;
  title: string;
  /** Short single-line summary that surfaces beneath the title. */
  summary: string;
  /** Optional path to deep-link into the matching surface. */
  href?: string;
}

export interface FindResult extends FindCandidate {
  matched: string;
}

/**
 * Run a contextual find. Returns a ranked subset of candidates whose title or
 * summary contains the query. Empty queries return the full list so the panel
 * can serve as a directory before any keystrokes.
 */
export function findInContext(
  query: string,
  candidates: FindCandidate[],
  scope?: FindScope,
): FindResult[] {
  const trimmed = query.trim().toLowerCase();
  const scoped = scope
    ? candidates.filter((candidate) => candidate.scope === scope)
    : candidates;
  if (!trimmed) {
    return scoped.map((candidate) => ({ ...candidate, matched: "" }));
  }
  return scoped
    .map((candidate) => {
      const haystack = `${candidate.title} ${candidate.summary}`.toLowerCase();
      const idx = haystack.indexOf(trimmed);
      if (idx < 0) return null;
      return { ...candidate, matched: trimmed, score: idx } as const;
    })
    .filter((value): value is NonNullable<typeof value> => value !== null)
    .sort((a, b) => a.score - b.score)
    .map(({ score: _score, ...rest }) => rest);
}

/**
 * Canonical saved-search categories (section 27.3). The panel pins these on
 * the rail so common diagnoses are one click away.
 */
export const SAVED_SEARCH_CATEGORIES = [
  "regressing-evals",
  "failed-tools",
  "expensive-turns",
  "pending-approvals",
  "migration-gaps",
  "audit-overrides",
] as const;

export type SavedSearchCategory = (typeof SAVED_SEARCH_CATEGORIES)[number];

export interface SavedSearch {
  id: string;
  name: string;
  category: SavedSearchCategory;
  scope: FindScope;
  query: string;
  /** ISO timestamp the user last opened this saved search. */
  lastUsed?: string;
}

export const DEFAULT_SAVED_SEARCHES: SavedSearch[] = [
  {
    id: "saved_regressing",
    name: "Regressing evals",
    category: "regressing-evals",
    scope: "eval",
    query: "regression",
  },
  {
    id: "saved_failed_tools",
    name: "Failed tools (last 24h)",
    category: "failed-tools",
    scope: "trace",
    query: "tool error",
  },
  {
    id: "saved_expensive",
    name: "Expensive turns",
    category: "expensive-turns",
    scope: "trace",
    query: "p95",
  },
  {
    id: "saved_approvals",
    name: "Pending approvals",
    category: "pending-approvals",
    scope: "audit",
    query: "approval",
  },
  {
    id: "saved_migration_gaps",
    name: "Migration gaps",
    category: "migration-gaps",
    scope: "migration",
    query: "unmapped",
  },
  {
    id: "saved_overrides",
    name: "Audit overrides",
    category: "audit-overrides",
    scope: "audit",
    query: "override",
  },
];

/**
 * Tiny client-side store for saved searches. The real implementation will be
 * server-backed; this module-scoped store gives the UI a deterministic surface
 * and lets the test suite verify add/remove/last-used semantics.
 */
class SavedSearchStore {
  private items: SavedSearch[];

  constructor(initial: SavedSearch[] = DEFAULT_SAVED_SEARCHES) {
    this.items = [...initial];
  }

  list(): SavedSearch[] {
    return [...this.items];
  }

  add(search: SavedSearch): SavedSearch[] {
    if (this.items.some((item) => item.id === search.id)) return this.list();
    this.items.push(search);
    return this.list();
  }

  remove(id: string): SavedSearch[] {
    this.items = this.items.filter((item) => item.id !== id);
    return this.list();
  }

  touch(id: string, when: string = new Date().toISOString()): SavedSearch[] {
    this.items = this.items.map((item) =>
      item.id === id ? { ...item, lastUsed: when } : item,
    );
    return this.list();
  }
}

export function createSavedSearchStore(initial?: SavedSearch[]): SavedSearchStore {
  return new SavedSearchStore(initial);
}

export type { SavedSearchStore };

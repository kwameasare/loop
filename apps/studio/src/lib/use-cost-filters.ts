/**
 * S285: Cost-filter hook — URL-synced + localStorage-persisted.
 *
 * • Reads initial state from URL search params (highest priority).
 * • Falls back to localStorage (last used settings).
 * • Falls back to EMPTY_FILTERS.
 * • On every change, writes to localStorage and updates URL search params
 *   without triggering a navigation (replaceState).
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  EMPTY_FILTERS,
  type CostFilters,
} from "./costs";

const STORAGE_KEY = "loop.cost.filters";
const FILTER_KEYS: (keyof CostFilters)[] = [
  "agent_id",
  "channel",
  "model",
  "date_from",
  "date_to",
];

function readFromUrl(): Partial<CostFilters> {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const out: Partial<CostFilters> = {};
  for (const k of FILTER_KEYS) {
    const v = params.get(k);
    if (v !== null) (out as Record<string, string>)[k] = v;
  }
  return out;
}

function readFromStorage(): Partial<CostFilters> {
  if (typeof localStorage === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<CostFilters>;
  } catch {
    return {};
  }
}

function writeToStorage(f: CostFilters): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(f));
  } catch {
    // quota error — silently ignore
  }
}

function writeToUrl(f: CostFilters): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  for (const k of FILTER_KEYS) {
    const v = f[k];
    if (v) {
      params.set(k, v);
    } else {
      params.delete(k);
    }
  }
  const search = params.toString();
  const newUrl =
    window.location.pathname + (search ? `?${search}` : "") + window.location.hash;
  window.history.replaceState(null, "", newUrl);
}

function mergeFilters(...sources: Partial<CostFilters>[]): CostFilters {
  const result: CostFilters = { ...EMPTY_FILTERS };
  for (const src of sources) {
    for (const k of FILTER_KEYS) {
      const v = (src as Record<string, string | undefined>)[k];
      if (v !== undefined && v !== "") {
        (result as Record<string, string>)[k] = v;
      }
    }
  }
  return result;
}

export function useCostFilters(): {
  filters: CostFilters;
  setFilters: (f: CostFilters) => void;
  resetFilters: () => void;
} {
  const [filters, setFiltersState] = useState<CostFilters>(() =>
    mergeFilters(readFromStorage(), readFromUrl()),
  );

  // On mount, sync URL params to localStorage (URL takes priority)
  useEffect(() => {
    const fromUrl = readFromUrl();
    if (Object.keys(fromUrl).length > 0) {
      setFiltersState((prev) => mergeFilters(prev, fromUrl));
    }
  }, []);

  const setFilters = useCallback((f: CostFilters) => {
    setFiltersState(f);
    writeToStorage(f);
    writeToUrl(f);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(EMPTY_FILTERS);
  }, [setFilters]);

  return { filters, setFilters, resetFilters };
}

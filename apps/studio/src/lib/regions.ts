/**
 * S594: region catalog + browser-side region inference.
 *
 * Single source of truth for the studio region selector. The catalog
 * mirrors the ``RegionName`` literal in ``openapi-types.ts`` so a
 * regen of the OpenAPI types will fail compilation here if the set
 * of legal regions ever changes — that drift is intentional and
 * forces an explicit doc/UI update.
 *
 * ``inferRegion()`` is a deliberately tiny heuristic: read the
 * browser's resolved IANA timezone and map ``Europe/*`` → ``eu-west``,
 * everything else → ``na-east``. We do NOT geo-locate the user from
 * IP (privacy + cookie-free). The auditor can confirm the heuristic
 * by reading this file.
 */

import type { RegionName } from "@/lib/openapi-types";

export interface RegionDescriptor {
  value: RegionName;
  label: string;
  /** Long form auditor-readable description shown under the dropdown. */
  description: string;
  /** Sample IANA TZ prefixes that should infer this region. */
  timezonePrefixes: readonly string[];
}

export const REGIONS: readonly RegionDescriptor[] = [
  {
    value: "na-east",
    label: "North America (na-east)",
    description: "Data resides in us-east-2. Lowest latency for the Americas.",
    timezonePrefixes: ["America/", "Pacific/", "US/", "Canada/"],
  },
  {
    value: "eu-west",
    label: "European Union (eu-west)",
    description: "Data resides in eu-west-1. GDPR residency for EU/EEA tenants.",
    timezonePrefixes: ["Europe/", "Africa/Ceuta", "Atlantic/Canary"],
  },
] as const;

export const DEFAULT_REGION: RegionName = "na-east";

/**
 * Infer the most plausible region for a new workspace using the
 * browser's resolved IANA timezone. Pure function so we can unit test
 * it without ``window``.
 */
export function inferRegionFromTimezone(timezone: string | undefined): RegionName {
  if (!timezone) return DEFAULT_REGION;
  for (const region of REGIONS) {
    for (const prefix of region.timezonePrefixes) {
      if (timezone === prefix || timezone.startsWith(prefix)) {
        return region.value;
      }
    }
  }
  return DEFAULT_REGION;
}

/**
 * Browser-only convenience wrapper. Returns ``DEFAULT_REGION`` on the
 * server (SSR) so we never crash the prerender; the client effect
 * re-runs once mounted.
 */
export function inferRegion(): RegionName {
  if (typeof Intl === "undefined") return DEFAULT_REGION;
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    return inferRegionFromTimezone(tz);
  } catch {
    return DEFAULT_REGION;
  }
}

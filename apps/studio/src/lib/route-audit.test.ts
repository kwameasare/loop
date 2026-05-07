import { readdirSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

import { describe, expect, it } from "vitest";

import {
  auditCopy,
  findOrphanRoutes,
  groupByVerb,
  IA_LIFECYCLE_VERBS,
  STUDIO_ROUTES,
} from "@/lib/route-audit";

const APP_ROOT = join(__dirname, "..", "app");

function discoverRoutes(): string[] {
  const routes: string[] = [];
  function walk(dir: string): void {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      const s = statSync(full);
      if (s.isDirectory()) {
        walk(full);
      } else if (entry === "page.tsx") {
        const rel = relative(APP_ROOT, dir).split(sep).join("/");
        routes.push(rel === "" ? "/" : `/${rel}`);
      }
    }
  }
  walk(APP_ROOT);
  return routes.sort();
}

describe("STUDIO_ROUTES", () => {
  it("registers every page under apps/studio/src/app", () => {
    const onDisk = discoverRoutes();
    const orphans = findOrphanRoutes(onDisk);
    expect(orphans, JSON.stringify(orphans, null, 2)).toEqual([]);
  });

  it("does not register concrete routes that are missing on disk", () => {
    const onDisk = new Set(discoverRoutes());
    const missing = STUDIO_ROUTES.filter(
      (entry) => !entry.route.includes("[") && !onDisk.has(entry.route),
    ).map((entry) => entry.route);
    expect(missing, JSON.stringify(missing, null, 2)).toEqual([]);
  });

  it("uses only canonical lifecycle verbs", () => {
    for (const entry of STUDIO_ROUTES) {
      expect(IA_LIFECYCLE_VERBS).toContain(entry.verb);
    }
  });

  it("groups routes by verb without dropping any", () => {
    const grouped = groupByVerb();
    const total = Object.values(grouped).reduce((n, list) => n + list.length, 0);
    expect(total).toBe(STUDIO_ROUTES.length);
  });

  it("anchors every route to the canonical UX standard", () => {
    for (const entry of STUDIO_ROUTES) {
      expect(entry.anchor).toMatch(/^§\d/);
    }
  });
});

describe("auditCopy", () => {
  it("is silent on friendly-precise copy", () => {
    expect(
      auditCopy([
        "Open the agent workbench and review behavior.",
        "Run the eval suite before promoting.",
      ]),
    ).toEqual([]);
  });

  it("flags flow-first language", () => {
    const findings = auditCopy([
      "Open the flow editor to start.",
      "Switch to the flow-first canvas.",
    ]);
    expect(findings).toHaveLength(2);
    expect(findings[0]?.matches).toContain("flow editor");
    expect(findings[1]?.matches).toContain("flow-first");
  });
});

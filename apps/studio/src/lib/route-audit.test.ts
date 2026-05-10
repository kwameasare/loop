import { readFileSync, readdirSync, statSync } from "node:fs";
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
const SRC_ROOT = join(__dirname, "..");

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

function discoverPageFiles(): {
  route: string;
  path: string;
  source: string;
}[] {
  const pages: { route: string; path: string; source: string }[] = [];
  function walk(dir: string): void {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      const s = statSync(full);
      if (s.isDirectory()) {
        walk(full);
      } else if (entry === "page.tsx") {
        const rel = relative(APP_ROOT, dir).split(sep).join("/");
        pages.push({
          route: rel === "" ? "/" : `/${rel}`,
          path: full,
          source: readFileSync(full, "utf8"),
        });
      }
    }
  }
  walk(APP_ROOT);
  return pages.sort((a, b) => a.route.localeCompare(b.route));
}

const ROUTE_FIXTURE_PATTERNS: readonly {
  label: string;
  pattern: RegExp;
}[] = [
  { label: "targetUxFixtures", pattern: /\btargetUxFixtures\b/ },
  { label: "explicit fixture mode", pattern: /\ballowFixture\s*:\s*true\b/ },
  { label: "fixture constant", pattern: /\bFIXTURE_[A-Z0-9_]+\b/ },
  { label: "voice stage fixture", pattern: /\bVOICE_STAGE_FIXTURE\b/ },
  {
    label: "marketplace demo catalog",
    pattern: /\bDEFAULT_MARKETPLACE_CATALOG\b/,
  },
];

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

  it("keeps voice under Build because it is one channel binding type", () => {
    const voiceRoute = STUDIO_ROUTES.find((entry) => entry.route === "/voice");
    expect(voiceRoute).toMatchObject({
      verb: "build",
      label: "Voice channel stage",
    });
    expect(voiceRoute?.purpose).toMatch(/one peer channel/i);
  });

  it("groups routes by verb without dropping any", () => {
    const grouped = groupByVerb();
    const total = Object.values(grouped).reduce(
      (n, list) => n + list.length,
      0,
    );
    expect(total).toBe(STUDIO_ROUTES.length);
  });

  it("anchors every route to the canonical UX standard", () => {
    for (const entry of STUDIO_ROUTES) {
      expect(entry.anchor).toMatch(/^§\d/);
    }
  });

  it("keeps route-facing pages out of fixture mode", () => {
    const findings = discoverPageFiles().flatMap((page) =>
      page.source.split("\n").flatMap((line, index) =>
        ROUTE_FIXTURE_PATTERNS.filter(({ pattern }) => pattern.test(line)).map(
          ({ label }) => ({
            route: page.route,
            line: index + 1,
            label,
            text: line.trim(),
          }),
        ),
      ),
    );

    expect(findings, JSON.stringify(findings, null, 2)).toEqual([]);
  });

  it("keeps workbench data libraries from defaulting to target UX fixtures", () => {
    const files = [
      "lib/agent-tools.ts",
      "lib/behavior.ts",
      "lib/conductor.ts",
      "lib/memory-studio.ts",
    ];
    const findings = files.flatMap((file) => {
      const source = readFileSync(join(SRC_ROOT, file), "utf8");
      return source.includes("targetUxFixtures") ? [file] : [];
    });

    expect(findings, JSON.stringify(findings, null, 2)).toEqual([]);
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

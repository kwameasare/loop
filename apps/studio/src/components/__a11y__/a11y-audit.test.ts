/**
 * S656 — a11y static-analysis audit gate.
 *
 * Walks the source of the top-10 studio pages and asserts five WCAG 2.1 AA
 * SCs at the JSX-source level. See ``apps/studio/a11y/AXE_AUDIT.md`` for
 * coverage and rationale. The gate replaces an axe-core sweep so the
 * studio doesn't take on an extra runtime dependency.
 *
 * Failures here MUST be treated as serious — they map directly to
 * WCAG 2.1 AA SC 1.1.1, 1.3.1, 2.4.6, 3.3.2, and 4.1.2.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../../../../..");

const TOP_PAGES: ReadonlyArray<{ name: string; path: string }> = [
  { name: "app-shell", path: "apps/studio/src/components/shell/app-shell.tsx" },
  { name: "inbox-queue", path: "apps/studio/src/components/inbox/inbox-queue.tsx" },
  {
    name: "conversation-viewer",
    path: "apps/studio/src/components/inbox/conversation-viewer.tsx",
  },
  { name: "agents-list", path: "apps/studio/src/components/agents/agents-list.tsx" },
  { name: "agent-tabs", path: "apps/studio/src/components/agents/agent-tabs.tsx" },
  {
    name: "eval-run-detail",
    path: "apps/studio/src/components/evals/eval-run-detail-view.tsx",
  },
  { name: "trace-list", path: "apps/studio/src/components/trace/trace-list.tsx" },
  { name: "cost-dashboard", path: "apps/studio/src/components/cost/cost-dashboard.tsx" },
  {
    name: "audit-log-page",
    path: "apps/studio/src/components/workspaces/audit-log-page.tsx",
  },
  {
    name: "enterprise-sso-form",
    path: "apps/studio/src/components/workspaces/enterprise-sso-form.tsx",
  },
];

function readSource(rel: string): string {
  return readFileSync(resolve(REPO_ROOT, rel), "utf8");
}

/** Strip JS/JSX comments so regex scans don't trip on them. */
function stripComments(src: string): string {
  return src
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/[^\n]*/g, "$1");
}

/**
 * Iterate over every JSX opening tag of the given element name and return
 * the attribute portion (everything between ``<name`` and the closing
 * ``>`` or ``/>``).
 */
function* openingTags(src: string, tag: string): Generator<string> {
  const cleaned = stripComments(src);
  const re = new RegExp(`<${tag}\\b([^>]*?)/?>`, "g");
  for (const m of cleaned.matchAll(re)) {
    yield m[1] ?? "";
  }
}

function hasAttr(tag: string, attr: string): boolean {
  return new RegExp(`\\b${attr}\\s*=`, "u").test(tag);
}

function hasAnyAttr(tag: string, attrs: readonly string[]): boolean {
  return attrs.some((a) => hasAttr(tag, a));
}

describe("a11y audit gate (WCAG 2.1 AA, S656)", () => {
  for (const page of TOP_PAGES) {
    describe(page.name, () => {
      const src = readSource(page.path);

      // SC 1.1.1 — non-text content.
      it("has alt on every <img>", () => {
        for (const attrs of openingTags(src, "img")) {
          expect(
            hasAttr(attrs, "alt"),
            `<img${attrs}> missing alt attribute`,
          ).toBe(true);
        }
      });

      // SC 1.3.1 / 3.3.2 — labels/instructions on form controls.
      it("every form control has a programmatic label", () => {
        for (const tag of ["input", "select", "textarea"] as const) {
          for (const attrs of openingTags(src, tag)) {
            // Hidden + submit buttons don't need labels.
            if (/\btype\s*=\s*"(?:hidden|submit|button|reset)"/.test(attrs)) {
              continue;
            }
            const labelled =
              hasAnyAttr(attrs, ["aria-label", "aria-labelledby", "id"]) ||
              /<label[\s\S]*?>[\s\S]*?<\s*input/.test(src) ||
              /<label[\s\S]*?>[\s\S]*?<\s*select/.test(src) ||
              /<label[\s\S]*?>[\s\S]*?<\s*textarea/.test(src);
            expect(
              labelled,
              `<${tag}${attrs}> in ${page.path} has no label, id, or aria-label*`,
            ).toBe(true);
          }
        }
      });

      // SC 2.4.6 — at least one heading or a landmark region per page.
      // Some leaf components are composed into a parent page that owns
      // the <h1>; in that case we require a landmark element so screen
      // readers still announce the section.
      it("renders at least one heading or landmark region", () => {
        const cleaned = stripComments(src);
        const hasHeading = /<h[1-6][\s>]/.test(cleaned);
        const hasLandmark =
          /<(?:section|header|main|nav|aside|article|form)\b/.test(cleaned) ||
          /role\s*=\s*"(?:heading|region|main|navigation|complementary|banner|form)"/.test(
            cleaned,
          );
        expect(
          hasHeading || hasLandmark,
          `${page.path} has no heading and no landmark element`,
        ).toBe(true);
      });

      // SC 4.1.2 — name, role, value on interactive controls.
      it("every <button> has accessible text or aria-label", () => {
        const cleaned = stripComments(src);
        const btnRe = /<button\b([^>]*?)>([\s\S]*?)<\/button>/g;
        for (const m of cleaned.matchAll(btnRe)) {
          const attrs = m[1] ?? "";
          const inner = (m[2] ?? "").replace(/<[^>]+>/g, "").trim();
          const ok = hasAnyAttr(attrs, ["aria-label", "aria-labelledby"]) ||
            inner.length > 0;
          expect(
            ok,
            `<button${attrs}>…</button> in ${page.path} has no accessible name`,
          ).toBe(true);
        }
      });

      // SC 4.1.2 — no <div onClick> without role+tabIndex (custom button).
      it("no <div onClick> acts as a button without role+tabIndex", () => {
        const cleaned = stripComments(src);
        const divRe = /<div\b([^>]*?)>/g;
        for (const m of cleaned.matchAll(divRe)) {
          const attrs = m[1] ?? "";
          if (!/\bonClick\s*=/.test(attrs)) continue;
          const okRole = /role\s*=\s*"(?:button|link)"/.test(attrs);
          const okTab = /tabIndex\s*=/.test(attrs);
          expect(
            okRole && okTab,
            `<div onClick> in ${page.path} must have role="button" + tabIndex`,
          ).toBe(true);
        }
      });
    });
  }

  it("audit report is committed", () => {
    const md = readSource("apps/studio/a11y/AXE_AUDIT.md");
    expect(md.length).toBeGreaterThan(500);
    expect(md).toMatch(/WCAG 2\.1/);
    expect(md).toMatch(/manual screen-reader pass/i);
    // All ten pages must appear in the report table.
    for (const p of TOP_PAGES) {
      const file = p.path.split("/").pop() ?? p.path;
      expect(
        md.includes(file),
        `report does not mention ${file}`,
      ).toBe(true);
    }
  });
});

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../../../../..");

function readSource(rel: string): string {
  return readFileSync(resolve(REPO_ROOT, rel), "utf8");
}

describe("canonical shell a11y smoke contract", () => {
  it("keeps the six-verb IA exposed as navigable sections", () => {
    const source = readSource(
      "apps/studio/src/components/shell/sidebar-nav.tsx",
    );

    for (const id of [
      "build",
      "test",
      "ship",
      "observe",
      "migrate",
      "govern",
    ]) {
      expect(source).toContain(`id: "${id}"`);
      expect(source).toContain("data-testid={`nav-section-${section.id}`}");
      expect(source).toContain('aria-current={active ? "page" : undefined}');
    }
  });

  it("keeps shell landmarks named for screen readers", () => {
    const shell = readSource("apps/studio/src/components/shell/app-shell.tsx");
    const preview = readSource(
      "apps/studio/src/components/shell/live-preview-rail.tsx",
    );
    const timeline = readSource(
      "apps/studio/src/components/shell/activity-timeline.tsx",
    );
    const footer = readSource(
      "apps/studio/src/components/shell/status-footer.tsx",
    );

    expect(shell).toContain('aria-label="Asset rail"');
    expect(shell).toContain('aria-label="Studio work surface"');
    expect(preview).toContain('data-testid="live-preview-rail"');
    expect(timeline).toContain('data-testid="activity-timeline"');
    expect(footer).toContain('data-testid="status-footer"');
  });

  it("keeps global focus and reduced-motion protections active", () => {
    const source = readSource("apps/studio/src/app/globals.css");

    expect(source).toContain(":focus-visible");
    expect(source).toContain("outline: 2px solid hsl(var(--focus))");
    expect(source).toContain("@media (prefers-reduced-motion: reduce)");
    expect(source).toContain("animation-duration: 1ms !important");
    expect(source).toContain("animation-iteration-count: 1 !important");
    expect(source).toContain("transition-duration: 1ms !important");
  });

  it("keeps status badges textual instead of color-only", () => {
    const source = readSource(
      "apps/studio/src/components/target/live-badge.tsx",
    );

    expect(source).toContain("children: ReactNode");
    expect(source).toContain('aria-hidden="true"');
    expect(source).toContain("{children}");
  });
});

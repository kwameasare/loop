"use client";

/**
 * UX404 — Responsive modes demo route.
 *
 * Lets QA force any responsive mode and verify the canonical surfaces from
 * §31 of the UX standard. The persistent second-monitor strip is rendered
 * regardless of mode (§31.4).
 */

import { useEffect, useState } from "react";

import { ResponsiveSurface } from "@/components/responsive";
import { ResponsiveModeSwitcher } from "@/components/shell/responsive-mode-switcher";
import { modeForViewport, type ResponsiveMode } from "@/lib/responsive";

export default function ResponsiveDemoPage(): JSX.Element {
  const [mode, setMode] = useState<ResponsiveMode>("desktop");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const sync = () => setMode(modeForViewport(window.innerWidth));
    sync();
    window.addEventListener("resize", sync);
    return () => window.removeEventListener("resize", sync);
  }, []);

  return (
    <main
      className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6"
      aria-label="Responsive modes"
    >
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Responsive modes</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Each mode keeps Studio capable: desktop has full power, tablet
            covers review and approval, mobile reserves the screen for urgent
            actions, and the large-display layout is built for war rooms.
          </p>
        </div>
        <ResponsiveModeSwitcher current={mode} onChange={setMode} />
      </header>
      <ResponsiveSurface mode={mode} />
    </main>
  );
}

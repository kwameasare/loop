"use client";

import { useEffect, useMemo, useState } from "react";
import { HelpCircle, Play, X } from "lucide-react";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { fetchHelpClips, type HelpClip } from "@/lib/help-telemetry";

function surfaceFromPath(pathname: string | null): string {
  if (!pathname) return "";
  if (pathname.startsWith("/deploy")) return "pipeline";
  if (pathname.startsWith("/replay") || pathname.startsWith("/traces")) {
    return "trace-theater";
  }
  if (pathname.startsWith("/voice")) return "voice-stage";
  if (pathname.startsWith("/migrate")) return "migration-atelier";
  if (pathname.startsWith("/enterprise")) return "govern";
  return pathname.split("/").filter(Boolean)[0] ?? "";
}

export function HelpClipLauncher(): JSX.Element {
  const pathname = usePathname();
  const surface = useMemo(() => surfaceFromPath(pathname), [pathname]);
  const [open, setOpen] = useState(false);
  const [clips, setClips] = useState<HelpClip[]>([]);
  const [activeClipId, setActiveClipId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;
      if (event.key === "?") {
        event.preventDefault();
        setOpen((current) => !current);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError(null);
    setClips([]);
    setActiveClipId(null);
    void fetchHelpClips(surface)
      .then((next) => {
        if (!cancelled) setClips(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Could not load help clips.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, surface]);

  return (
    <>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Open contextual help"
        title="Show me"
        onClick={() => setOpen((current) => !current)}
      >
        <HelpCircle className="h-4 w-4" aria-hidden={true} />
      </Button>
      {open ? (
        <aside
          className="fixed bottom-4 right-4 z-50 w-[min(22rem,calc(100vw-2rem))] rounded-md border bg-popover p-3 text-popover-foreground shadow-lg"
          data-testid="help-clip-card"
          aria-label="Show me help clips"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Show me</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Contextual clips stay muted until you press play.
              </p>
            </div>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              aria-label="Close contextual help"
              onClick={() => setOpen(false)}
            >
              <X className="h-4 w-4" aria-hidden={true} />
            </Button>
          </div>
          <ul className="mt-3 space-y-2">
            {error ? (
              <li
                className="rounded-md border border-warning/40 bg-warning/10 p-2 text-xs text-warning"
                role="status"
              >
                {error}
              </li>
            ) : null}
            {clips.map((clip) => (
              <li key={clip.clip_id} className="instrument-panel rounded-xl p-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium">
                    {clip.title ?? clip.surface}
                  </p>
                  <span className="text-xs text-muted-foreground">
                    {clip.duration}s
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {clip.transcript}
                </p>
                <button
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-primary"
                  type="button"
                  aria-label={`Play ${clip.clip_id} muted`}
                  onClick={() =>
                    setActiveClipId((current) =>
                      current === clip.clip_id ? null : clip.clip_id,
                    )
                  }
                >
                  <Play className="h-3.5 w-3.5" aria-hidden={true} />
                  {activeClipId === clip.clip_id
                    ? "Hide muted clip"
                    : "Play muted clip"}
                </button>
                {activeClipId === clip.clip_id ? (
                  <div
                    className="mt-3 rounded-md border bg-background p-2"
                    data-testid="inline-help-clip"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold">
                        Muted clip playing
                      </span>
                      <span className="font-mono text-[0.65rem] text-muted-foreground">
                        {clip.url}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-1">
                      {(clip.frames?.length ? clip.frames : [clip.transcript]).map(
                        (frame, index, frames) => (
                          <div key={`${clip.clip_id}-${index}`} className="space-y-1">
                            <div
                              className="h-1 rounded-full bg-muted"
                              aria-hidden={true}
                            >
                              <div
                                className="h-full rounded-full bg-primary transition-all duration-gentle"
                                style={{
                                  width: `${Math.round(
                                    ((index + 1) / frames.length) * 100,
                                  )}%`,
                                }}
                              />
                            </div>
                            <p className="text-xs text-muted-foreground">
                              {frame}
                            </p>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        </aside>
      ) : null}
    </>
  );
}

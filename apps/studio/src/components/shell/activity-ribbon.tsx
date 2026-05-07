"use client";

import { useEffect, useState } from "react";

import { cpJson } from "@/lib/ux-wireup";
import { useActiveWorkspace } from "@/lib/use-active-workspace";

interface ActivityModel {
  turn_rate_per_minute: number;
  ribbon_intensity: number;
  tone: "live" | "quiet";
}

export function ActivityRibbon(): JSX.Element {
  const { active } = useActiveWorkspace();
  const [activity, setActivity] = useState<ActivityModel>({
    turn_rate_per_minute: 0,
    ribbon_intensity: 0.08,
    tone: "quiet",
  });

  useEffect(() => {
    if (!active) return;
    let cancelled = false;
    void cpJson<ActivityModel>(
      `/workspaces/${encodeURIComponent(active.id)}/activity`,
      {
        fallback: {
          turn_rate_per_minute: 0,
          ribbon_intensity: 0.08,
          tone: "quiet",
        },
      },
    ).then((next) => {
      if (!cancelled) setActivity(next);
    });
    return () => {
      cancelled = true;
    };
  }, [active]);

  const opacity = Math.max(0.18, Math.min(0.9, activity.ribbon_intensity));
  const width = `${Math.max(12, Math.round(activity.ribbon_intensity * 100))}%`;
  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-muted"
      aria-hidden="true"
      data-testid="workspace-activity-ribbon"
      title={`${activity.turn_rate_per_minute} turns/min`}
    >
      <div
        className="h-full bg-gradient-to-r from-success via-info to-warning transition-all duration-700 ease-standard"
        style={{ width, opacity }}
      />
    </div>
  );
}

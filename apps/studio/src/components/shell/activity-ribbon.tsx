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
  const activeWorkspaceId = active?.id;
  const [activity, setActivity] = useState<ActivityModel>({
    turn_rate_per_minute: 0,
    ribbon_intensity: 0,
    tone: "quiet",
  });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!activeWorkspaceId) return;
    setLoaded(false);
    if (activeWorkspaceId === "local-workspace") {
      setActivity({
        turn_rate_per_minute: 0,
        ribbon_intensity: 0,
        tone: "quiet",
      });
      return;
    }
    let cancelled = false;
    void cpJson<ActivityModel>(
      `/workspaces/${encodeURIComponent(activeWorkspaceId)}/activity`,
      {
        allowFallback: false,
        fallback: {
          turn_rate_per_minute: 0,
          ribbon_intensity: 0,
          tone: "quiet",
        },
      },
    )
      .then((next) => {
        if (!cancelled) {
          setActivity(next);
          setLoaded(true);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setActivity({
            turn_rate_per_minute: 0,
            ribbon_intensity: 0,
            tone: "quiet",
          });
          setLoaded(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeWorkspaceId]);

  const opacity = loaded
    ? Math.max(0.18, Math.min(0.9, activity.ribbon_intensity))
    : 0;
  const width = loaded
    ? `${Math.max(12, Math.round(activity.ribbon_intensity * 100))}%`
    : "0%";
  return (
    <div
      className="pointer-events-none absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-muted"
      aria-hidden="true"
      data-testid="workspace-activity-ribbon"
      title={loaded ? `${activity.turn_rate_per_minute} turns/min` : "Activity unavailable"}
    >
      <div
        className="activity-ribbon-flow h-full bg-gradient-to-r from-success via-info via-primary to-warning transition-all duration-700 ease-standard"
        data-testid="workspace-activity-ribbon-fill"
        style={{ width, opacity }}
      />
    </div>
  );
}

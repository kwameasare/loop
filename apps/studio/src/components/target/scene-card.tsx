import type { TargetScene } from "@/lib/target-ux";
import { cn } from "@/lib/utils";

import { LiveBadge } from "./live-badge";

export interface SceneCardProps {
  scene: TargetScene;
  className?: string;
}

export function SceneCard({ scene, className }: SceneCardProps) {
  return (
    <article
      className={cn("rounded-md border bg-card p-4", className)}
      data-testid="scene-card"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{scene.name}</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            {scene.domain} - {scene.turns} turns - {scene.source}
          </p>
        </div>
        <LiveBadge tone={scene.evalLinked ? "live" : "draft"}>
          {scene.evalLinked ? "Eval linked" : "Unlinked"}
        </LiveBadge>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{scene.summary}</p>
    </article>
  );
}

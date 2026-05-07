import { Circle, Copy, Map, TriangleAlert } from "lucide-react";

import { ConfidenceMeter, LiveBadge } from "@/components/target";
import type {
  EmbeddingClusterPoint,
  EmbeddingsExplorerModel,
} from "@/lib/knowledge-diagnostics";
import { cn } from "@/lib/utils";

const QUALITY_TONE: Record<EmbeddingClusterPoint["quality"], string> = {
  healthy: "border-success bg-success text-success-foreground",
  outlier: "border-warning bg-warning text-warning-foreground",
  duplicate: "border-info bg-info text-info-foreground",
  stale: "border-destructive bg-destructive text-destructive-foreground",
};

const QUALITY_ICON = {
  healthy: Circle,
  outlier: TriangleAlert,
  duplicate: Copy,
  stale: TriangleAlert,
} satisfies Record<EmbeddingClusterPoint["quality"], typeof Circle>;

export function EmbeddingsExplorer({
  model,
}: {
  model: EmbeddingsExplorerModel;
}) {
  return (
    <section
      aria-labelledby="embeddings-explorer-heading"
      className="space-y-3"
      data-testid="embeddings-explorer"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            Embeddings Explorer
          </p>
          <h2 className="mt-1 text-lg font-semibold" id="embeddings-explorer-heading">
            Knowledge map with accessible table fallback
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Clusters, outliers, near-duplicates, stale chunks, and accidental
            citations become visible without relying on color alone.
          </p>
        </div>
        <LiveBadge tone="live">{model.points.length} chunks mapped</LiveBadge>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div
          className="relative min-h-[28rem] overflow-hidden rounded-md border bg-card p-4"
          role="img"
          aria-label="Embedding cluster map"
        >
          <div className="absolute inset-4 rounded-md border border-dashed border-border bg-muted/20" />
          {model.clusters.map((cluster, index) => (
            <div
              key={cluster.id}
              className={cn(
                "absolute rounded-full border border-border bg-background/80 px-3 py-2 text-xs shadow-sm",
                index === 0 && "left-[10%] top-[12%]",
                index === 1 && "right-[12%] top-[24%]",
                index === 2 && "bottom-[15%] left-[32%]",
              )}
            >
              <p className="font-semibold">{cluster.label}</p>
              <p className="text-muted-foreground">{cluster.chunkCount} chunks</p>
            </div>
          ))}
          {model.points.map((point) => {
            const Icon = QUALITY_ICON[point.quality];
            return (
              <button
                key={point.id}
                type="button"
                className={cn(
                  "absolute flex h-9 w-9 items-center justify-center rounded-full border shadow-sm transition-transform duration-swift hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus",
                  QUALITY_TONE[point.quality],
                )}
                style={{ left: `${point.x}%`, top: `${point.y}%` }}
                aria-label={`${point.label}: ${point.quality}, ${point.citedCount} citations`}
                title={`${point.label} - ${point.quality}`}
              >
                <Icon className="h-4 w-4" aria-hidden={true} />
              </button>
            );
          })}
          <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 rounded-md border bg-background/90 p-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Circle className="h-3 w-3" /> healthy
            </span>
            <span className="inline-flex items-center gap-1">
              <TriangleAlert className="h-3 w-3" /> outlier or stale
            </span>
            <span className="inline-flex items-center gap-1">
              <Copy className="h-3 w-3" /> duplicate
            </span>
          </div>
        </div>

        <div className="space-y-3">
          {model.clusters.map((cluster) => (
            <article key={cluster.id} className="rounded-md border bg-card p-4">
              <div className="flex items-start gap-3">
                <Map className="mt-0.5 h-5 w-5 text-info" aria-hidden={true} />
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-semibold">{cluster.label}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {cluster.summary}
                  </p>
                  <ConfidenceMeter
                    className="mt-3"
                    value={cluster.health}
                    label="Cluster health"
                    evidence={`${cluster.chunkCount} chunks in cluster`}
                  />
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border bg-card">
        <table className="min-w-full divide-y text-sm">
          <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-semibold" scope="col">
                Chunk
              </th>
              <th className="px-3 py-2 font-semibold" scope="col">
                Cluster
              </th>
              <th className="px-3 py-2 font-semibold" scope="col">
                Quality
              </th>
              <th className="px-3 py-2 font-semibold" scope="col">
                Citations
              </th>
              <th className="px-3 py-2 font-semibold" scope="col">
                Evidence
              </th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {model.tableFallback.map((point) => (
              <tr key={point.id}>
                <td className="px-3 py-3 font-medium">{point.label}</td>
                <td className="px-3 py-3">{point.cluster}</td>
                <td className="px-3 py-3">{point.quality}</td>
                <td className="px-3 py-3 tabular-nums">{point.citedCount}</td>
                <td className="px-3 py-3 text-xs text-muted-foreground">
                  {point.evidenceRef}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { KbList } from "@/components/agents/kb-list";
import { EmbeddingsExplorer } from "@/components/knowledge/embeddings-explorer/embeddings-explorer";
import { InverseRetrievalLab } from "@/components/knowledge/inverse-retrieval/inverse-retrieval-lab";
import {
  ConfidenceMeter,
  EvidenceCallout,
  LiveBadge,
  StatePanel,
} from "@/components/target";
import {
  deleteKbDocument,
  triggerDocRefresh,
  uploadKbDocument,
  type DeleteKbDocumentInput,
  type KbDocument,
  type UploadKbDocumentInput,
} from "@/lib/kb";
import {
  buildEmbeddingsExplorerModel,
  buildInverseRetrievalModel,
  fetchInverseRetrievalModel,
} from "@/lib/knowledge-diagnostics";
import {
  formatScore,
  getKnowledgeAtelierModel,
  sourceKindLabel,
  type KnowledgeAtelierModel,
  type KnowledgeSource,
  type KnowledgeSyncStatus,
  type RetrievalCandidate,
} from "@/lib/knowledge";

export interface KnowledgeAtelierProps {
  agentId: string;
  initialDocuments: KbDocument[];
}

function statusTone(
  status: KnowledgeSyncStatus,
): "live" | "staged" | "canary" | "paused" {
  if (status === "ready") return "live";
  if (status === "indexing") return "staged";
  if (status === "error" || status === "stale") return "canary";
  return "paused";
}

function statusState(
  status: KnowledgeSyncStatus,
): "success" | "loading" | "error" | "stale" | "degraded" {
  if (status === "ready") return "success";
  if (status === "indexing") return "loading";
  if (status === "error") return "error";
  if (status === "stale") return "stale";
  return "degraded";
}

function signedScore(score: number): string {
  return formatScore(score);
}

function SourceHealthCard({ source }: { source: KnowledgeSource }) {
  return (
    <article
      className="rounded-md border bg-card p-4"
      data-testid={`knowledge-source-${source.documentId}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase text-muted-foreground">
            {sourceKindLabel(source.kind)}
          </p>
          <h3 className="mt-1 font-semibold">{source.name}</h3>
        </div>
        <LiveBadge tone={statusTone(source.syncStatus)}>
          {source.syncStatus}
        </LiveBadge>
      </div>
      <dl className="mt-4 grid gap-3 text-sm 2xl:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase text-muted-foreground">
            Freshness
          </dt>
          <dd>{source.freshness}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-muted-foreground">
            Owner
          </dt>
          <dd>{source.owner}</dd>
        </div>
        <div className="2xl:col-span-2">
          <dt className="text-xs font-semibold uppercase text-muted-foreground">
            Access
          </dt>
          <dd>{source.accessRules}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-muted-foreground">
            Chunks
          </dt>
          <dd>{source.chunkCount}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase text-muted-foreground">
            Sensitivity
          </dt>
          <dd>{source.sensitivity}</dd>
        </div>
      </dl>
      <ConfidenceMeter
        className="mt-4"
        evidence={`Eval coverage evidence: ${source.evidence}`}
        label="Eval coverage"
        value={source.evalCoverage}
      />
      {source.errors.length > 0 ? (
        <StatePanel
          className="mt-4"
          state={statusState(source.syncStatus)}
          title="Source needs attention"
        >
          {source.errors.join("; ")}
        </StatePanel>
      ) : null}
    </article>
  );
}

function CandidateScoreTable({
  candidates,
  emptyTitle,
}: {
  candidates: RetrievalCandidate[];
  emptyTitle: string;
}) {
  if (candidates.length === 0) {
    return (
      <StatePanel state="empty" title={emptyTitle}>
        Index a source with embeddings before retrieval candidates can be
        scored.
      </StatePanel>
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border">
      <table className="min-w-full divide-y text-sm">
        <thead className="bg-muted/40 text-left text-xs uppercase text-muted-foreground">
          <tr>
            <th className="px-3 py-2 font-semibold" scope="col">
              Rank
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Chunk
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Hybrid
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Semantic
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Keyword
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Metadata
            </th>
            <th className="px-3 py-2 font-semibold" scope="col">
              Freshness
            </th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {candidates.map((candidate) => (
            <tr
              key={candidate.id}
              data-testid={`retrieval-candidate-${candidate.rank}`}
            >
              <td className="px-3 py-3 align-top tabular-nums">
                #{candidate.rank}
              </td>
              <td className="max-w-sm px-3 py-3 align-top">
                <p className="font-medium">{candidate.chunkId}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {candidate.citationPreview}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  {candidate.missedReason ?? candidate.snippet}
                </p>
              </td>
              <td className="px-3 py-3 align-top tabular-nums">
                {signedScore(candidate.scores.hybrid)}
              </td>
              <td className="px-3 py-3 align-top tabular-nums">
                {signedScore(candidate.scores.semantic)}
              </td>
              <td className="px-3 py-3 align-top tabular-nums">
                {signedScore(candidate.scores.keyword)}
              </td>
              <td className="px-3 py-3 align-top tabular-nums">
                {signedScore(candidate.scores.metadata)}
              </td>
              <td className="px-3 py-3 align-top tabular-nums">
                {signedScore(candidate.scores.freshness)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReadinessList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border p-3">
      <h4 className="text-sm font-semibold">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">None detected.</p>
      ) : (
        <ul className="mt-2 space-y-1 text-sm">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function KnowledgeAtelier({
  agentId,
  initialDocuments,
}: KnowledgeAtelierProps) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [query, setQuery] = useState("");
  const [savedEval, setSavedEval] = useState<string | null>(null);
  const [liveInverseModel, setLiveInverseModel] = useState<ReturnType<
    typeof buildInverseRetrievalModel
  > | null>(null);

  const model: KnowledgeAtelierModel = useMemo(
    () => getKnowledgeAtelierModel(agentId, documents),
    [agentId, documents],
  );
  const inverseModel = useMemo(
    () => buildInverseRetrievalModel(model),
    [model],
  );
  useEffect(() => {
    let cancelled = false;
    setLiveInverseModel(null);
    void fetchInverseRetrievalModel(agentId, model).then((next) => {
      if (!cancelled) setLiveInverseModel(next);
    });
    return () => {
      cancelled = true;
    };
  }, [agentId, model]);
  const embeddingsModel = useMemo(
    () => buildEmbeddingsExplorerModel(model),
    [model],
  );
  const activeQuery = query.trim() || model.retrievalLab.defaultQuery;

  async function upload(input: UploadKbDocumentInput): Promise<KbDocument> {
    const doc = await uploadKbDocument(input);
    setDocuments((current) => [doc, ...current]);
    return doc;
  }

  async function remove(
    input: DeleteKbDocumentInput,
  ): Promise<{ documentId: string }> {
    const result = await deleteKbDocument(input);
    setDocuments((current) =>
      current.filter((document) => document.id !== input.documentId),
    );
    return result;
  }

  async function refresh(agent: string, documentId: string) {
    const status = await triggerDocRefresh(agent, documentId);
    setDocuments((current) =>
      current.map((document) =>
        document.id === documentId
          ? { ...document, lastRefreshedAt: status.lastRunAt }
          : document,
      ),
    );
    return status;
  }

  return (
    <main className="flex flex-col gap-6" data-testid="knowledge-atelier">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <p className="text-xs font-medium uppercase text-muted-foreground">
            Build / Knowledge Atelier
          </p>
          <h1 className="mt-1 text-2xl font-semibold">Knowledge Atelier</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Inspect source health, chunking, retrieval ranking, and readiness
            for {model.agentName}.
          </p>
        </div>
        <LiveBadge tone={model.sources.length > 0 ? "live" : "paused"}>
          {model.sources.length} sources
        </LiveBadge>
      </header>

      <section
        aria-labelledby="knowledge-sources-heading"
        className="space-y-3"
        data-testid="knowledge-sources"
      >
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2
              className="text-lg font-semibold"
              id="knowledge-sources-heading"
            >
              Sources and sync health
            </h2>
            <p className="text-sm text-muted-foreground">
              Freshness, ownership, access, sync errors, chunk counts, eval
              coverage, and sensitivity stay visible together.
            </p>
          </div>
        </div>
        {model.sources.length === 0 ? (
          <StatePanel state="empty" title="No knowledge sources indexed">
            Upload a file or connect a source before retrieval, chunking, and
            readiness can produce evidence.
          </StatePanel>
        ) : (
          <div className="grid gap-3 2xl:grid-cols-2">
            {model.sources.map((source) => (
              <SourceHealthCard key={source.id} source={source} />
            ))}
          </div>
        )}
        <div className="rounded-md border bg-card p-4">
          <KbList
            agentId={agentId}
            initialDocuments={documents}
            remove={remove}
            triggerRefresh={refresh}
            upload={upload}
          />
        </div>
      </section>

      <section
        aria-labelledby="knowledge-chunks-heading"
        className="space-y-3"
        data-testid="knowledge-chunks"
      >
        <div>
          <h2 className="text-lg font-semibold" id="knowledge-chunks-heading">
            Visible chunking
          </h2>
          <p className="text-sm text-muted-foreground">
            Each chunk keeps document lineage, overlap, metadata, permissions,
            embedding preview, version history, and cited usage in view.
          </p>
        </div>
        {model.chunks.length === 0 ? (
          <StatePanel state="degraded" title="No chunks available">
            Indexing has not produced chunks yet, so retrieval explanations are
            unsupported.
          </StatePanel>
        ) : (
          <div className="grid gap-3 2xl:grid-cols-3">
            {model.chunks.slice(0, 6).map((chunk) => (
              <article
                className="rounded-md border bg-card p-4"
                data-testid={`knowledge-chunk-${chunk.id}`}
                key={chunk.id}
              >
                <p className="text-xs font-medium uppercase text-muted-foreground">
                  {chunk.originalDocument} / {chunk.chunkRange}
                </p>
                <p className="mt-2 text-sm">{chunk.text}</p>
                <dl className="mt-3 grid gap-2 text-xs text-muted-foreground">
                  <div>
                    <dt className="font-semibold uppercase">Overlap</dt>
                    <dd>{chunk.overlapTokens} tokens</dd>
                  </div>
                  <div>
                    <dt className="font-semibold uppercase">Metadata</dt>
                    <dd>{chunk.metadata.join(", ")}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold uppercase">Embeddings</dt>
                    <dd>
                      {chunk.embeddingPreview.length > 0
                        ? chunk.embeddingPreview.join(", ")
                        : "Unavailable"}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-semibold uppercase">Permissions</dt>
                    <dd>{chunk.permissions}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold uppercase">Version history</dt>
                    <dd>{chunk.versionHistory}</dd>
                  </div>
                  <div>
                    <dt className="font-semibold uppercase">Cited usage</dt>
                    <dd>{chunk.citedUsage}</dd>
                  </div>
                </dl>
              </article>
            ))}
          </div>
        )}
      </section>

      <section
        aria-labelledby="retrieval-lab-heading"
        className="space-y-3"
        data-testid="retrieval-lab"
      >
        <div>
          <h2 className="text-lg font-semibold" id="retrieval-lab-heading">
            Retrieval Lab
          </h2>
          <p className="text-sm text-muted-foreground">
            Type a query, inspect top-k chunks, compare hybrid score components,
            and save the query as a retrieval eval.
          </p>
        </div>
        <div className="rounded-md border bg-card p-4">
          <label
            className="text-xs font-semibold uppercase text-muted-foreground"
            htmlFor="retrieval-query"
          >
            Query
          </label>
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <input
              className="min-w-0 flex-1 rounded-md border bg-background px-3 py-2 text-sm"
              id="retrieval-query"
              onChange={(event) => {
                setQuery(event.target.value);
                setSavedEval(null);
              }}
              placeholder={model.retrievalLab.defaultQuery}
              value={query}
            />
            <button
              className="rounded-md border bg-background px-3 py-2 text-sm font-medium target-transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              disabled={model.retrievalLab.candidates.length === 0}
              onClick={() =>
                setSavedEval(
                  `Saved retrieval eval seed for "${activeQuery}" from ${model.retrievalLab.evalSeedEvidence}`,
                )
              }
              type="button"
            >
              Save as retrieval eval
            </button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Filters: {model.retrievalLab.metadataFilters.join(", ")}. Top-k:{" "}
            {model.retrievalLab.topK}.
          </p>
          {savedEval ? (
            <p className="mt-3 text-sm text-info" role="status">
              {savedEval}
            </p>
          ) : null}
        </div>
        <CandidateScoreTable
          candidates={model.retrievalLab.candidates}
          emptyTitle="No scored retrieval candidates"
        />
        <div className="rounded-md border bg-card p-4">
          <h3 className="text-sm font-semibold">Answer preview</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {model.retrievalLab.answerPreview}
          </p>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Missed candidates</h3>
          <CandidateScoreTable
            candidates={model.retrievalLab.missedCandidates}
            emptyTitle="No missed candidates"
          />
        </div>
      </section>

      <InverseRetrievalLab model={liveInverseModel ?? inverseModel} />
      <EmbeddingsExplorer model={embeddingsModel} />

      <section
        aria-labelledby="why-panel-heading"
        className="grid gap-3 2xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]"
        data-testid="retrieval-why-panel"
      >
        <div>
          <h2 className="text-lg font-semibold" id="why-panel-heading">
            Why panel
          </h2>
          <p className="text-sm text-muted-foreground">
            Trace retrievals explain ranking without inventing telemetry: query,
            filters, losing candidates, document version, and staleness are
            explicit.
          </p>
        </div>
        {model.whyPanel ? (
          <EvidenceCallout
            confidence={model.whyPanel.confidence}
            source={model.whyPanel.evidence}
            title={model.whyPanel.title}
            tone="info"
          >
            {model.whyPanel.rankedReason}
          </EvidenceCallout>
        ) : (
          <StatePanel state="empty" title="No retrieval to explain">
            Run a retrieval after indexing completes to populate the Why panel.
          </StatePanel>
        )}
        {model.whyPanel ? (
          <dl className="grid gap-3 rounded-md border bg-card p-4 text-sm 2xl:col-span-2 2xl:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Sent query
              </dt>
              <dd>{model.whyPanel.sentQuery}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Filters applied
              </dt>
              <dd>{model.whyPanel.filtersApplied.join(", ")}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Candidates lost
              </dt>
              <dd>
                {model.whyPanel.candidatesLost.length > 0
                  ? model.whyPanel.candidatesLost.join("; ")
                  : "None lost after filtering"}
              </dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Document version
              </dt>
              <dd>{model.whyPanel.versionAnswered}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase text-muted-foreground">
                Source freshness
              </dt>
              <dd>{model.whyPanel.sourceFreshness}</dd>
            </div>
          </dl>
        ) : null}
      </section>

      <section
        aria-labelledby="readiness-heading"
        className="space-y-3"
        data-testid="knowledge-readiness"
      >
        <div>
          <h2 className="text-lg font-semibold" id="readiness-heading">
            Readiness report
          </h2>
          <p className="text-sm text-muted-foreground">
            After ingestion, the report calls out answerability, duplicates,
            stale sources, missing metadata, eval seeds, citation quality, and
            sensitive data risk.
          </p>
        </div>
        <div className="grid gap-3 2xl:grid-cols-[minmax(0,0.8fr)_minmax(0,2fr)]">
          <EvidenceCallout
            confidence={model.readiness.citationQualityEstimate}
            source={model.readiness.evidence}
            title="Readiness recommendation"
            tone={
              model.readiness.citationQualityEstimate >= 65
                ? "success"
                : "warning"
            }
          >
            {model.readiness.recommendation}
          </EvidenceCallout>
          <div className="grid gap-3 2xl:grid-cols-2">
            <ReadinessList
              items={model.readiness.answerableQuestions}
              title="Likely answerable"
            />
            <ReadinessList
              items={model.readiness.unanswerableQuestions}
              title="Likely unanswerable"
            />
            <ReadinessList
              items={model.readiness.duplicateSources}
              title="Duplicate sources"
            />
            <ReadinessList
              items={model.readiness.staleSources}
              title="Stale sources"
            />
            <ReadinessList
              items={model.readiness.missingMetadata}
              title="Missing metadata"
            />
            <ReadinessList
              items={model.readiness.generatedEvalCases}
              title="Generated eval cases"
            />
            <ReadinessList
              items={model.readiness.sensitiveDataWarnings}
              title="Sensitive data warnings"
            />
          </div>
        </div>
      </section>
    </main>
  );
}

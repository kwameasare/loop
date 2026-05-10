"use client";

import { useEffect, useMemo, useState } from "react";

import { KbList } from "@/components/agents/kb-list";
import { PersonalizedEmptyStateSuggestions } from "@/components/empty-state/personalized-empty-state-suggestions";
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
  markKnowledgeChunkSuperseded as defaultMarkKnowledgeChunkSuperseded,
  saveRetrievalEvalCase as defaultSaveRetrievalEvalCase,
  sourceKindLabel,
  type KnowledgeAtelierModel,
  type KnowledgeSource,
  type KnowledgeSyncStatus,
  type RetrievalEvalCaseInput,
  type RetrievalEvalCaseResult,
  type RetrievalCandidate,
  type SupersedeKnowledgeChunkInput,
  type SupersedeKnowledgeChunkResult,
} from "@/lib/knowledge";

export interface KnowledgeAtelierProps {
  agentId: string;
  initialDocuments: KbDocument[];
  degradedReason?: string | undefined;
  focusedFilter?: string | undefined;
  focusedView?: string | undefined;
  supersedeChunk?: (
    agentId: string,
    chunkId: string,
    input: SupersedeKnowledgeChunkInput,
  ) => Promise<SupersedeKnowledgeChunkResult>;
  saveRetrievalEval?: (
    agentId: string,
    input: RetrievalEvalCaseInput,
  ) => Promise<RetrievalEvalCaseResult>;
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
  degradedReason,
  focusedFilter,
  focusedView,
  supersedeChunk = defaultMarkKnowledgeChunkSuperseded,
  saveRetrievalEval = defaultSaveRetrievalEvalCase,
}: KnowledgeAtelierProps) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [query, setQuery] = useState("");
  const [savedEval, setSavedEval] = useState<RetrievalEvalCaseResult | null>(
    null,
  );
  const [savingEval, setSavingEval] = useState(false);
  const [saveEvalError, setSaveEvalError] = useState<string | null>(null);
  const [supersededChunkIds, setSupersededChunkIds] = useState<string[]>([]);
  const [supersedingChunkId, setSupersedingChunkId] = useState<string | null>(
    null,
  );
  const [supersedeError, setSupersedeError] = useState<string | null>(null);
  const [liveInverseModel, setLiveInverseModel] = useState<ReturnType<
    typeof buildInverseRetrievalModel
  > | null>(null);
  const [liveInverseError, setLiveInverseError] = useState<string | null>(null);

  const model: KnowledgeAtelierModel = useMemo(
    () => getKnowledgeAtelierModel(agentId, documents),
    [agentId, documents],
  );
  const inverseModel = useMemo(
    () => ({ ...buildInverseRetrievalModel(model), misses: [] }),
    [model],
  );
  useEffect(() => {
    let cancelled = false;
    setLiveInverseModel(null);
    setLiveInverseError(null);
    void fetchInverseRetrievalModel(agentId, model)
      .then((next) => {
        if (!cancelled) setLiveInverseModel(next);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLiveInverseError(
            err instanceof Error
              ? err.message
              : "Could not load inverse retrieval diagnostics.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [agentId, model]);
  const embeddingsModel = useMemo(
    () => buildEmbeddingsExplorerModel(model),
    [model],
  );
  const staleFocused = focusedFilter === "stale";
  const retrievalFocused = focusedView === "retrieval";
  const displayedSources = useMemo(() => {
    if (!staleFocused) return model.sources;
    return model.sources.filter(
      (source) =>
        source.syncStatus === "stale" || source.syncStatus === "error",
    );
  }, [model.sources, staleFocused]);
  const activeQuery = query.trim() || model.retrievalLab.defaultQuery;
  const topCandidate = model.retrievalLab.candidates[0];

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

  async function markSuperseded(chunkId: string) {
    setSupersedingChunkId(chunkId);
    setSupersedeError(null);
    try {
      await supersedeChunk(agentId, chunkId, {
        reason:
          "Builder marked this chunk superseded from Knowledge Atelier review.",
        replacement_hint: "Review newer source version before retrieval use.",
      });
      setSupersededChunkIds((current) =>
        current.includes(chunkId) ? current : [...current, chunkId],
      );
    } catch (err) {
      setSupersedeError(
        err instanceof Error
          ? err.message
          : "Could not mark the chunk superseded.",
      );
    } finally {
      setSupersedingChunkId(null);
    }
  }

  async function saveRetrievalSeed() {
    if (!topCandidate) return;
    setSavingEval(true);
    setSavedEval(null);
    setSaveEvalError(null);
    try {
      const result = await saveRetrievalEval(agentId, {
        query: activeQuery,
        topChunkId: topCandidate.chunkId,
        candidateChunkIds: model.retrievalLab.candidates.map(
          (candidate) => candidate.chunkId,
        ),
        metadataFilters: model.retrievalLab.metadataFilters,
        expectedCitation: topCandidate.citationPreview,
        evidenceRef: model.retrievalLab.evalSeedEvidence,
        missedCandidateIds: model.retrievalLab.missedCandidates.map(
          (candidate) => candidate.chunkId,
        ),
      });
      setSavedEval(result);
    } catch (err) {
      setSaveEvalError(
        err instanceof Error
          ? err.message
          : "Could not save this retrieval query as an eval case.",
      );
    } finally {
      setSavingEval(false);
    }
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

      {focusedView || focusedFilter ? (
        <section
          className="rounded-md border border-info/40 bg-info/5 p-3 text-sm text-info"
          data-testid="knowledge-focused-query"
        >
          <p className="font-medium">Opened from an evidence link.</p>
          <p className="mt-1 text-xs">
            {retrievalFocused
              ? "Retrieval diagnostics are highlighted below."
              : null}
            {staleFocused
              ? ` Stale-source filter is active: ${displayedSources.length} source${
                  displayedSources.length === 1 ? "" : "s"
                } need attention.`
              : null}
            {!retrievalFocused && !staleFocused
              ? ` Requested view=${focusedView ?? "none"} filter=${
                  focusedFilter ?? "none"
                }.`
              : null}
          </p>
        </section>
      ) : null}

      <section
        aria-labelledby="knowledge-sources-heading"
        className={`space-y-3 ${
          staleFocused ? "rounded-md ring-2 ring-focus ring-offset-2 ring-offset-background" : ""
        }`}
        data-testid="knowledge-sources"
        data-focused={staleFocused ? "true" : "false"}
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
        {degradedReason ? (
          <StatePanel state="degraded" title="Knowledge service unavailable">
            {degradedReason}
          </StatePanel>
        ) : model.sources.length === 0 ? (
          <div>
            <StatePanel state="empty" title="No knowledge sources indexed">
              Upload a file or connect a source before retrieval, chunking, and
              readiness can produce evidence.
            </StatePanel>
            <PersonalizedEmptyStateSuggestions agentId={agentId} surface="kb" />
          </div>
        ) : staleFocused && displayedSources.length === 0 ? (
          <StatePanel state="success" title="No stale sources found">
            The stale-document evidence link resolved to this agent, and the
            loaded source set has no stale or failed syncs.
          </StatePanel>
        ) : (
          <div className="grid gap-3 2xl:grid-cols-2">
            {displayedSources.map((source) => (
              <SourceHealthCard key={source.id} source={source} />
            ))}
          </div>
        )}
        <div className="rounded-md border bg-card p-4">
          <KbList
            agentId={agentId}
            degradedReason={degradedReason}
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
            {model.chunks.slice(0, 6).map((chunk) => {
              const locallySuperseded = supersededChunkIds.includes(chunk.id);
              const lifecycle = locallySuperseded
                ? "superseded"
                : chunk.lifecycle;
              return (
                <article
                  className="rounded-md border bg-card p-4"
                  data-testid={`knowledge-chunk-${chunk.id}`}
                  key={chunk.id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-xs font-medium uppercase text-muted-foreground">
                      {chunk.originalDocument} / {chunk.chunkRange}
                    </p>
                    <span
                      className="rounded-md border bg-background px-2 py-0.5 text-[0.7rem] font-medium"
                      data-testid={`knowledge-chunk-lifecycle-${chunk.id}`}
                    >
                      {lifecycle}
                    </span>
                  </div>
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
                      <dt className="font-semibold uppercase">
                        Version history
                      </dt>
                      <dd>{chunk.versionHistory}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold uppercase">Cited usage</dt>
                      <dd>{chunk.citedUsage}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold uppercase">
                        Affected policies
                      </dt>
                      <dd>{chunk.affectedPolicies.join(", ")}</dd>
                    </div>
                    <div>
                      <dt className="font-semibold uppercase">
                        Affected evals
                      </dt>
                      <dd>{chunk.affectedEvals.join(", ")}</dd>
                    </div>
                  </dl>
                  <button
                    type="button"
                    className="mt-3 rounded-md border bg-background px-3 py-2 text-xs font-medium hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                    data-testid={`knowledge-supersede-${chunk.id}`}
                    disabled={
                      lifecycle === "superseded" ||
                      supersedingChunkId === chunk.id
                    }
                    onClick={() => void markSuperseded(chunk.id)}
                  >
                    {supersedingChunkId === chunk.id
                      ? "Marking..."
                      : lifecycle === "superseded"
                        ? "Superseded"
                        : "Mark superseded"}
                  </button>
                </article>
              );
            })}
          </div>
        )}
        {supersedeError ? (
          <p
            className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
            role="alert"
          >
            {supersedeError}
          </p>
        ) : null}
      </section>

      <section
        aria-labelledby="retrieval-lab-heading"
        className={`space-y-3 ${
          retrievalFocused
            ? "rounded-md ring-2 ring-focus ring-offset-2 ring-offset-background"
            : ""
        }`}
        data-testid="retrieval-lab"
        data-focused={retrievalFocused ? "true" : "false"}
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
                setSaveEvalError(null);
              }}
              placeholder={model.retrievalLab.defaultQuery}
              value={query}
            />
            <button
              className="rounded-md border bg-background px-3 py-2 text-sm font-medium target-transition hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
              disabled={!topCandidate || savingEval}
              onClick={() => void saveRetrievalSeed()}
              type="button"
            >
              {savingEval ? "Saving eval..." : "Save as retrieval eval"}
            </button>
          </div>
          <p className="mt-2 text-xs text-muted-foreground">
            Filters: {model.retrievalLab.metadataFilters.join(", ")}. Top-k:{" "}
            {model.retrievalLab.topK}.
          </p>
          {savedEval ? (
            <p className="mt-3 text-sm text-info" role="status">
              Retrieval eval {savedEval.case_id} saved from{" "}
              {model.retrievalLab.evalSeedEvidence}.
            </p>
          ) : null}
          {saveEvalError ? (
            <p
              className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive"
              role="alert"
            >
              {saveEvalError}
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

      <InverseRetrievalLab
        model={liveInverseModel ?? inverseModel}
        unavailableReason={liveInverseError}
      />
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
              items={model.readiness.capabilityCoverage.map(
                (item) =>
                  `${item.capability}: ${item.coverage}% (${item.evidence})`,
              )}
              title="Capability coverage"
            />
            <ReadinessList
              items={model.readiness.contradictions.map(
                (item) =>
                  `${item.severity}: ${item.summary} Policies ${item.affectedPolicies.join(", ")}; evals ${item.affectedEvals.join(", ")}`,
              )}
              title="Contradiction impact"
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

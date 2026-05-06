import { targetUxFixtures } from "@/lib/target-ux";
import type { KbDocument } from "@/lib/kb";

export type KnowledgeSourceKind =
  | "file"
  | "url"
  | "crawled_site"
  | "docs_site"
  | "notion"
  | "google_drive"
  | "sharepoint"
  | "zendesk"
  | "intercom"
  | "slack"
  | "database"
  | "custom_sync";

export type KnowledgeSyncStatus =
  | "ready"
  | "indexing"
  | "error"
  | "stale"
  | "unsupported";

export type KnowledgeSensitivity =
  | "public"
  | "internal"
  | "confidential"
  | "restricted";

export interface KnowledgeSource {
  id: string;
  documentId: string;
  name: string;
  kind: KnowledgeSourceKind;
  freshness: string;
  owner: string;
  accessRules: string;
  syncStatus: KnowledgeSyncStatus;
  errors: string[];
  chunkCount: number;
  evalCoverage: number;
  sensitivity: KnowledgeSensitivity;
  evidence: string;
  confidence: number;
}

export interface KnowledgeChunk {
  id: string;
  sourceId: string;
  sourceName: string;
  originalDocument: string;
  chunkRange: string;
  text: string;
  overlapTokens: number;
  metadata: string[];
  embeddingPreview: number[];
  permissions: string;
  versionHistory: string;
  citedUsage: string;
  evidence: string;
}

export interface RetrievalScoreBreakdown {
  hybrid: number;
  semantic: number;
  keyword: number;
  metadata: number;
  freshness: number;
}

export interface RetrievalCandidate {
  id: string;
  rank: number;
  chunkId: string;
  sourceName: string;
  snippet: string;
  citationPreview: string;
  filters: string[];
  scores: RetrievalScoreBreakdown;
  missedReason?: string;
}

export interface RetrievalLab {
  defaultQuery: string;
  topK: number;
  metadataFilters: string[];
  candidates: RetrievalCandidate[];
  missedCandidates: RetrievalCandidate[];
  answerPreview: string;
  evalSeedEvidence: string;
}

export interface RetrievalWhyPanel {
  title: string;
  rankedReason: string;
  sentQuery: string;
  filtersApplied: string[];
  candidatesLost: string[];
  versionAnswered: string;
  sourceFreshness: string;
  evidence: string;
  confidence: number;
}

export interface KnowledgeReadinessReport {
  answerableQuestions: string[];
  unanswerableQuestions: string[];
  duplicateSources: string[];
  staleSources: string[];
  missingMetadata: string[];
  generatedEvalCases: string[];
  citationQualityEstimate: number;
  sensitiveDataWarnings: string[];
  recommendation: string;
  evidence: string;
}

export interface KnowledgeAtelierModel {
  agentId: string;
  agentName: string;
  sources: KnowledgeSource[];
  chunks: KnowledgeChunk[];
  retrievalLab: RetrievalLab;
  whyPanel: RetrievalWhyPanel | null;
  readiness: KnowledgeReadinessReport;
}

const REFERENCE_NOW = new Date("2026-05-06T00:00:00Z");

const KIND_LABELS: Record<KnowledgeSourceKind, string> = {
  file: "File",
  url: "URL",
  crawled_site: "Crawled site",
  docs_site: "Docs site",
  notion: "Notion",
  google_drive: "Google Drive",
  sharepoint: "SharePoint",
  zendesk: "Zendesk",
  intercom: "Intercom",
  slack: "Slack",
  database: "Database",
  custom_sync: "Custom sync",
};

function daysSince(iso: string | null): number | null {
  if (!iso) return null;
  const millis = REFERENCE_NOW.getTime() - new Date(iso).getTime();
  return Math.max(0, Math.round(millis / 86_400_000));
}

function inferKind(doc: KbDocument): KnowledgeSourceKind {
  const name = doc.name.toLowerCase();
  if (name.startsWith("http") || name.endsWith(".url")) return "url";
  if (name.includes("notion")) return "notion";
  if (name.includes("zendesk")) return "zendesk";
  if (name.includes("slack")) return "slack";
  if (name.includes("sharepoint")) return "sharepoint";
  if (name.includes("drive")) return "google_drive";
  if (name.includes("intercom")) return "intercom";
  if (name.includes("crawl")) return "crawled_site";
  if (name.includes("docs")) return "docs_site";
  if (/\b(db|database)\b/.test(name.replace(/[_-]/g, " "))) {
    return "database";
  }
  if (name.includes("sync")) return "custom_sync";
  return "file";
}

function freshnessFor(doc: KbDocument): string {
  if (doc.status === "indexing") return "Syncing now; freshness pending";
  if (doc.status === "error") return "Last sync failed";
  const days = daysSince(doc.lastRefreshedAt ?? doc.uploadedAt);
  if (days === null) return "Never refreshed";
  if (days === 0) return "Fresh today";
  if (days === 1) return "Fresh 1 day ago";
  return `Fresh ${days} days ago`;
}

function syncStatusFor(doc: KbDocument): KnowledgeSyncStatus {
  if (doc.status === "error") return "error";
  if (doc.status === "indexing") return "indexing";
  const days = daysSince(doc.lastRefreshedAt ?? doc.uploadedAt);
  if (typeof days === "number" && days > 30) return "stale";
  return "ready";
}

function sensitivityFor(doc: KbDocument): KnowledgeSensitivity {
  const name = doc.name.toLowerCase();
  if (name.includes("legal") || name.includes("policy")) return "confidential";
  if (name.includes("pii") || name.includes("secret")) return "restricted";
  if (name.includes("public") || name.includes("faq")) return "public";
  return "internal";
}

function sourceConfidence(status: KnowledgeSyncStatus): number {
  if (status === "ready") return 88;
  if (status === "stale") return 56;
  if (status === "indexing") return 42;
  if (status === "error") return 24;
  return 10;
}

function sourceOwner(index: number): string {
  const owners = ["Support Ops", "CX Policy", "Knowledge Lead", "Trust Review"];
  return owners[index % owners.length]!;
}

function sourceAccessRules(kind: KnowledgeSourceKind): string {
  if (kind === "slack")
    return "Inherited channel membership; private channels excluded";
  if (kind === "google_drive" || kind === "sharepoint") {
    return "Inherited document ACL; external shares blocked";
  }
  if (kind === "database")
    return "Read-only service role; tenant filter required";
  return "Workspace members with support role; no public sharing";
}

function evalCoverageFor(doc: KbDocument, index: number): number {
  if (doc.status === "error") return 12;
  if (doc.status === "indexing") return 0;
  return Math.max(36, 82 - index * 9);
}

function chunkCountFor(doc: KbDocument): number {
  if (doc.status === "error") return 0;
  return Math.max(1, Math.ceil(doc.bytes / 4096));
}

export function sourceKindLabel(kind: KnowledgeSourceKind): string {
  return KIND_LABELS[kind];
}

export function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function buildSources(agentId: string, docs: KbDocument[]): KnowledgeSource[] {
  return docs.map((doc, index) => {
    const kind = inferKind(doc);
    const syncStatus = syncStatusFor(doc);
    const errors =
      syncStatus === "error"
        ? ["Indexing failed before embeddings were written"]
        : syncStatus === "stale"
          ? ["Refresh is older than the 30 day readiness target"]
          : [];
    return {
      id: `ks_${doc.id}`,
      documentId: doc.id,
      name: doc.name,
      kind,
      freshness: freshnessFor(doc),
      owner: sourceOwner(index),
      accessRules: sourceAccessRules(kind),
      syncStatus,
      errors,
      chunkCount: chunkCountFor(doc),
      evalCoverage: evalCoverageFor(doc, index),
      sensitivity: sensitivityFor(doc),
      evidence: `KB document ${doc.id} for agent ${agentId}; uploaded ${doc.uploadedAt}`,
      confidence: sourceConfidence(syncStatus),
    };
  });
}

function chunkTextFor(source: KnowledgeSource, index: number): string {
  if (source.syncStatus === "indexing") {
    return "Chunk preview pending while embeddings are created.";
  }
  if (source.syncStatus === "error") {
    return "Chunk preview unavailable because the last indexing run failed.";
  }
  if (source.name === "support_handbook.md") {
    return [
      "Fixture excerpt: refund grace periods, escalation owners, and citation requirements for support replies.",
      "Fixture excerpt: warranty exceptions require order age, region, and final-sale metadata before an answer is drafted.",
      "Fixture excerpt: sensitive account evidence must be summarized, not quoted, in customer-facing responses.",
    ][index % 3]!;
  }
  return `Fixture excerpt from ${source.name}: retrieval-ready policy guidance with source metadata preserved.`;
}

function buildChunks(sources: KnowledgeSource[]): KnowledgeChunk[] {
  return sources.flatMap((source) => {
    const visibleCount = Math.min(Math.max(source.chunkCount, 1), 3);
    return Array.from({ length: visibleCount }, (_, index) => ({
      id: `${source.id}_chunk_${index + 1}`,
      sourceId: source.id,
      sourceName: source.name,
      originalDocument: source.name,
      chunkRange: `chunk ${index + 1} of ${source.chunkCount || 1}`,
      text: chunkTextFor(source, index),
      overlapTokens: source.syncStatus === "ready" ? 48 : 0,
      metadata: [
        `kind:${source.kind}`,
        `sensitivity:${source.sensitivity}`,
        `owner:${source.owner}`,
      ],
      embeddingPreview:
        source.syncStatus === "ready" ? [0.12, -0.04, 0.31, 0.08] : [],
      permissions: source.accessRules,
      versionHistory:
        source.syncStatus === "ready"
          ? "v3 current; v2 retained for citation diff"
          : "No version history available until a successful sync",
      citedUsage:
        source.evalCoverage > 0
          ? `${Math.round(source.evalCoverage / 10)} eval citations in the last run`
          : "No eval citations yet",
      evidence: `Chunk preview is anchored to ${source.evidence}`,
    }));
  });
}

function buildRetrievalLab(chunks: KnowledgeChunk[]): RetrievalLab {
  const query = "Can I refund a final-sale order after the grace period?";
  const candidates = chunks.slice(0, 3).map((chunk, index) => {
    const semantic = Math.max(0.52, 0.91 - index * 0.12);
    const keyword = Math.max(0.4, 0.76 - index * 0.1);
    const metadata = index === 0 ? 0.88 : 0.62;
    const freshness = chunk.embeddingPreview.length ? 0.84 : 0.22;
    const hybrid =
      semantic * 0.45 + keyword * 0.25 + metadata * 0.2 + freshness * 0.1;
    return {
      id: `candidate_${chunk.id}`,
      rank: index + 1,
      chunkId: chunk.id,
      sourceName: chunk.sourceName,
      snippet: chunk.text,
      citationPreview: `${chunk.originalDocument} / ${chunk.chunkRange}`,
      filters: ["workspace:acme-support", "sensitivity:allowed", "locale:any"],
      scores: { hybrid, semantic, keyword, metadata, freshness },
    };
  });
  const missedCandidates = chunks.slice(3, 5).map((chunk, index) => ({
    id: `missed_${chunk.id}`,
    rank: candidates.length + index + 1,
    chunkId: chunk.id,
    sourceName: chunk.sourceName,
    snippet: chunk.text,
    citationPreview: `${chunk.originalDocument} / ${chunk.chunkRange}`,
    filters: ["metadata mismatch"],
    scores: {
      hybrid: 0.38 - index * 0.04,
      semantic: 0.54,
      keyword: 0.25,
      metadata: 0.18,
      freshness: 0.68,
    },
    missedReason:
      index === 0
        ? "Lost to missing region metadata"
        : "Lost to lower keyword overlap after stemming",
  }));

  return {
    defaultQuery: query,
    topK: Math.max(3, candidates.length),
    metadataFilters: [
      "locale:any",
      "source:not deprecated",
      "sensitivity <= confidential",
    ],
    candidates,
    missedCandidates,
    answerPreview:
      candidates.length > 0
        ? "Answer preview: final-sale refunds need an exception policy citation and escalation owner before the agent can promise a refund."
        : "Answer preview unavailable until at least one indexed chunk is ready.",
    evalSeedEvidence:
      candidates.length > 0
        ? `Retrieval eval can seed from ${candidates[0]!.chunkId}`
        : "Unsupported: no retrieval candidates to save as an eval yet",
  };
}

function buildWhyPanel(retrievalLab: RetrievalLab): RetrievalWhyPanel | null {
  const top = retrievalLab.candidates[0];
  if (!top) return null;
  return {
    title: `Why ${top.chunkId} ranked #1`,
    rankedReason:
      "It had the strongest semantic match, passed sensitivity filters, and was fresher than the losing candidates.",
    sentQuery: retrievalLab.defaultQuery,
    filtersApplied: top.filters,
    candidatesLost: retrievalLab.missedCandidates.map(
      (candidate) => `${candidate.chunkId}: ${candidate.missedReason}`,
    ),
    versionAnswered: top.citationPreview,
    sourceFreshness: `Freshness score ${formatScore(top.scores.freshness)}`,
    evidence: `Retrieval score breakdown for ${top.id}`,
    confidence: Math.round(top.scores.hybrid * 100),
  };
}

function buildReadiness(
  sources: KnowledgeSource[],
  retrievalLab: RetrievalLab,
): KnowledgeReadinessReport {
  const staleSources = sources
    .filter((source) => source.syncStatus === "stale")
    .map((source) => source.name);
  const errorSources = sources
    .filter((source) => source.syncStatus === "error")
    .map((source) => source.name);
  const lowCoverage = sources
    .filter((source) => source.evalCoverage < 50)
    .map((source) => source.name);
  const duplicateSources = sources
    .filter(
      (source, index, all) =>
        all.findIndex((candidate) => candidate.name === source.name) !== index,
    )
    .map((source) => source.name);
  const sensitive = sources
    .filter(
      (source) =>
        source.sensitivity === "confidential" ||
        source.sensitivity === "restricted",
    )
    .map((source) => `${source.name} is ${source.sensitivity}`);

  return {
    answerableQuestions:
      retrievalLab.candidates.length > 0
        ? [
            "Refund exception policy",
            "Escalation owner for final-sale disputes",
            "Citation requirement before customer-facing answer",
          ]
        : [],
    unanswerableQuestions:
      sources.length === 0
        ? ["No knowledge sources are indexed for this agent yet"]
        : [
            "Region-specific warranty exception without metadata",
            "Deprecated source behavior after access revocation",
          ],
    duplicateSources,
    staleSources,
    missingMetadata: Array.from(new Set([...lowCoverage, ...errorSources])),
    generatedEvalCases:
      retrievalLab.candidates.length > 0
        ? [
            "retrieval.final_sale_refund.requires_exception",
            "retrieval.sensitive_account_summary.no_quote",
          ]
        : [],
    citationQualityEstimate:
      sources.length === 0
        ? 0
        : Math.round(
            sources.reduce((sum, source) => sum + source.evalCoverage, 0) /
              sources.length,
          ),
    sensitiveDataWarnings: sensitive,
    recommendation:
      errorSources.length > 0
        ? "Fix failed syncs before this knowledge base can gate production answers."
        : staleSources.length > 0
          ? "Refresh stale sources and regenerate retrieval evals before deploy."
          : "Ready for retrieval eval gating; review low-coverage metadata next.",
    evidence:
      sources.length > 0
        ? `Readiness derived from ${sources.length} source records and ${retrievalLab.candidates.length} retrieval candidates`
        : "Unsupported: no source, chunk, or retrieval evidence is available",
  };
}

export function getKnowledgeAtelierModel(
  agentId: string,
  docs: KbDocument[],
): KnowledgeAtelierModel {
  const agent =
    targetUxFixtures.agents.find((candidate) => candidate.id === agentId) ??
    targetUxFixtures.agents[0];
  const sources = buildSources(agentId, docs);
  const chunks = buildChunks(sources);
  const retrievalLab = buildRetrievalLab(chunks);
  return {
    agentId,
    agentName: agent?.name ?? "Agent",
    sources,
    chunks,
    retrievalLab,
    whyPanel: buildWhyPanel(retrievalLab),
    readiness: buildReadiness(sources, retrievalLab),
  };
}

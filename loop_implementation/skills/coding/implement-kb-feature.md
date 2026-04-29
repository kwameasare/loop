---
name: implement-kb-feature
description: Use when modifying the knowledge-base (RAG) engine — sources, ingestion pipeline, chunking, embedding, retrieval, vision indexing, citations.
when_to_use: |
  - Adding a new source type (Notion, Confluence, GDrive, S3, Postgres SQL, Slack threads).
  - Changing the chunking strategy or adding a new strategy.
  - Swapping embedding providers or supporting a new one.
  - Modifying retrieval (hybrid search, reranker, top-k, similarity threshold).
  - Implementing vision indexing.
  - Changing how citations are returned.
required_reading:
  - architecture/ARCHITECTURE.md      # §3.7 KB engine
  - architecture/CLOUD_PORTABILITY.md # §3 vector backend mapping
  - data/SCHEMA.md                    # §2.3 knowledge_bases + §3.x kb_chunks (Qdrant + Postgres metadata)
  - engineering/PERFORMANCE.md        # §1.2 Qdrant top-k target
  - engineering/ERROR_CODES.md        # KB prefix
  - adrs/README.md                    # ADR-002 (Qdrant), ADR-019 (chunking)
applies_to: coding
owner: Founding Eng #1 (Runtime) / Eng #4 secondary
last_reviewed: 2026-04-29
---

# Implement KB feature

## Trigger

Changes under `packages/kb-engine/`. KB quality is one of the top-3 customer-visible factors; a regression here shows up in eval scorers immediately.

## Required reading

1. ADR-002 (Qdrant default), ADR-019 (chunking strategies, per-bot override).
2. `architecture/ARCHITECTURE.md` §3.7 (full KB engine spec).
3. `engineering/PERFORMANCE.md` §1.2 ("Qdrant top-k=10 (5M points) ≤ 25ms p99").

## Steps

1. **Source ingestion** (adding a new source type):
   - Implement `IngestSource` protocol: `discover()`, `fetch()`, `metadata()`.
   - Idempotent — re-running ingestion on the same source updates only changed docs (content hash compared).
   - Status flow: `queued` → `indexing` → `indexed` | `failed` (`kb_documents.status`).
   - Outsource web crawling to Firecrawl per existing pattern.
2. **Chunking** (new strategies must be opt-in via `chunk_strategy` config):
   - Strategies: `semantic_boundary` (default), `fixed_size`, `sliding_window`, `table_aware` (Unstructured.io), `code_aware` (tree-sitter).
   - Each chunk carries `byte_start` / `byte_end` / `position` so citations can point back.
   - Chunk size limits: aim 200–800 tokens; never exceed 2000.
3. **Embedding** (provider changes):
   - Pluggable. Default `text-embedding-3-large` (3072 dim). Other supported: Voyage, Cohere, BGE, GTE, NV-Embed.
   - `vector_dim` is per-KB; once set, immutable (changing it requires a full re-index).
   - Embedding calls go through the LLM gateway (cost is captured the same way).
4. **Vector store** (default Qdrant):
   - Per-workspace collections (`kb_<workspace_id_short>_<kb_id_short>`). NEVER shared.
   - Quantization: enable binary on collections > 5M points.
   - pgvector remains supported for self-hosters at small scale via a backend flag.
5. **Retrieval**:
   - Hybrid by default: BM25 + vector, weighted 0.4 / 0.6 (configurable per-bot).
   - Optional reranker (Cohere Rerank, BGE-reranker) — adds 60–120ms; off by default.
   - Returns `RetrievalChunk` with `chunk_id`, `doc_id`, `score`, `content`, `source_uri`, `byte_range`.
6. **Confidence + fallback**:
   - Every retrieval returns confidence (max similarity score).
   - Agents can branch on confidence threshold (`if confidence < 0.6: respond with "I don't know"`).
   - Configurable per-bot in `agent_kb_grants.scope`.
7. **Vision indexing**:
   - PDF pages with charts/diagrams routed through a vision model (Claude Sonnet, GPT-4o-vision, or self-hostable InternVL).
   - Output: structured text representation stored alongside the page chunk.
   - Tag pages as `vision_indexed: true` in `kb_documents.metadata_json`.
8. **Citations** in agent responses:
   - When the agent calls the KB tool, the result includes `cited_chunks` with byte-range source links.
   - The agent's response renderer (in channel adapters) can format citations per the channel.
   - `citation_presence` eval scorer asserts coverage.
9. **Tests**:
   - Unit: chunking determinism, embedding stability (fixture vectors), retrieval precision/recall on a fixture KB.
   - Integration: ingest a real PDF/MD/HTML, retrieve, verify citations match.
   - Eval: at least one eval suite case per source type.
10. **Bench**: top-k=10 latency on a 5M-point collection ≤ 25ms p99. Run `pytest --benchmark-only -k kb_retrieval`.
11. **Docs**: update `architecture/ARCHITECTURE.md` §3.7 if behavior changed; update `data/SCHEMA.md` if schema changed.
12. **PR.** Tag Eng #1 + Eng #4 (eval-impact reviewer).

## Definition of done

- [ ] Tracker story claimed before work (status `In progress`) and closed after (`Done` + PR ref) — see `meta/update-tracker.md`.
- [ ] Per-workspace collection scoping enforced.
- [ ] Idempotent ingestion (content-hash-based skip).
- [ ] Citations carry byte ranges.
- [ ] Confidence available in retrieval results.
- [ ] Chunking strategy documented and tested.
- [ ] Vision indexing covered (if applicable).
- [ ] p99 latency budget met.
- [ ] Eval suite has at least one case for the changed path.

## Anti-patterns

- ❌ Cross-workspace Qdrant collection access.
- ❌ Re-embedding unchanged docs.
- ❌ Hard-coding embedding dim in code (read from KB config).
- ❌ Citations without byte ranges.
- ❌ "Hallucinate when KB is empty" — always fall back to "I don't know" if confidence < threshold.

## Related skills

- `data/add-postgres-migration.md` if KB metadata schema changes.
- `data/update-schema.md` for documenting changes.
- `testing/write-eval-suite.md` for KB cases.
- `testing/perf-check.md` for retrieval latency.

## References

- ADR-002, ADR-019.
- `architecture/ARCHITECTURE.md` §3.7.
- `engineering/PERFORMANCE.md` §1.2.

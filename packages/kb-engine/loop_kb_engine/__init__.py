"""Loop KB engine: documents -> chunks -> embeddings -> retrieval.

Public surface:

* `Document` / `Chunk` -- pydantic v2 strict frozen models.
* `Chunker` -- fixed-size + semantic-boundary chunkers.
* `EmbeddingService` Protocol + `DeterministicEmbeddingService` test stub.
* `VectorStore` Protocol; `InMemoryVectorStore` for fast tests;
  `QdrantRestVectorStore` for dependency-light integration and prod wiring.
* `KnowledgeBase` -- ties chunker + embedder + store + BM25 lexical
  index together to provide hybrid retrieval (alpha-weighted).
"""

from loop_kb_engine.chunker import (
    Chunker,
    FixedSizeChunker,
    HeadingChunker,
    SemanticChunker,
)
from loop_kb_engine.crawler import (
    CrawlResult,
    CrawlStats,
    SitemapCrawler,
)
from loop_kb_engine.embeddings import (
    DeterministicEmbeddingService,
    EmbeddingService,
)
from loop_kb_engine.kb import KnowledgeBase, RetrievalResult
from loop_kb_engine.layout_chunker import ChunkType, LayoutAwareChunker
from loop_kb_engine.lexical_postgres import LexicalHit, PostgresLexicalIndex
from loop_kb_engine.models import Chunk, Document, EmbeddingVector
from loop_kb_engine.parsers import (
    DocumentParseError,
    Parser,
    ParserRegistry,
    TextParser,
    UnsupportedDocumentType,
    default_registry,
)
from loop_kb_engine.perf_fixture import (
    DEFAULT_CHUNK_COUNT,
    DEFAULT_TOP_K,
    TARGET_P50_MS,
    SyntheticKBHit,
    SyntheticMillionChunkFixture,
)
from loop_kb_engine.qdrant_store import QdrantRestVectorStore, qdrant_collection_name
from loop_kb_engine.retrieval import (
    ChunkDiff,
    TombstoneRegistry,
    chunk_content_hash,
    diff_chunks,
    rrf_combine,
)
from loop_kb_engine.scheduler import (
    DocRefreshConfig,
    DocRefreshRecord,
    RefreshScheduler,
    RefreshStatus,
)
from loop_kb_engine.store import InMemoryVectorStore, VectorStore

__all__ = [
    "DEFAULT_CHUNK_COUNT",
    "DEFAULT_TOP_K",
    "TARGET_P50_MS",
    "Chunk",
    "ChunkDiff",
    "ChunkType",
    "Chunker",
    "CrawlResult",
    "CrawlStats",
    "DeterministicEmbeddingService",
    "DocRefreshConfig",
    "DocRefreshRecord",
    "Document",
    "DocumentParseError",
    "EmbeddingService",
    "EmbeddingVector",
    "FixedSizeChunker",
    "HeadingChunker",
    "InMemoryVectorStore",
    "KnowledgeBase",
    "LayoutAwareChunker",
    "LexicalHit",
    "Parser",
    "ParserRegistry",
    "PostgresLexicalIndex",
    "QdrantRestVectorStore",
    "RefreshScheduler",
    "RefreshStatus",
    "RetrievalResult",
    "SemanticChunker",
    "SitemapCrawler",
    "SyntheticKBHit",
    "SyntheticMillionChunkFixture",
    "TextParser",
    "TombstoneRegistry",
    "UnsupportedDocumentType",
    "VectorStore",
    "chunk_content_hash",
    "default_registry",
    "diff_chunks",
    "qdrant_collection_name",
    "rrf_combine",
]

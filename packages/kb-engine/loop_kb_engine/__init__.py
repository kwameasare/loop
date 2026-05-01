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
from loop_kb_engine.embeddings import (
    DeterministicEmbeddingService,
    EmbeddingService,
)
from loop_kb_engine.kb import KnowledgeBase, RetrievalResult
from loop_kb_engine.models import Chunk, Document, EmbeddingVector
from loop_kb_engine.parsers import (
    DocumentParseError,
    Parser,
    ParserRegistry,
    TextParser,
    UnsupportedDocumentType,
    default_registry,
)
from loop_kb_engine.qdrant_store import QdrantRestVectorStore, qdrant_collection_name
from loop_kb_engine.retrieval import (
    ChunkDiff,
    TombstoneRegistry,
    chunk_content_hash,
    diff_chunks,
    rrf_combine,
)
from loop_kb_engine.store import InMemoryVectorStore, VectorStore

__all__ = [
    "Chunk",
    "ChunkDiff",
    "Chunker",
    "DeterministicEmbeddingService",
    "Document",
    "DocumentParseError",
    "EmbeddingService",
    "EmbeddingVector",
    "FixedSizeChunker",
    "HeadingChunker",
    "InMemoryVectorStore",
    "KnowledgeBase",
    "Parser",
    "ParserRegistry",
    "QdrantRestVectorStore",
    "RetrievalResult",
    "SemanticChunker",
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

"""Loop KB engine: documents -> chunks -> embeddings -> retrieval.

Public surface:

* `Document` / `Chunk` -- pydantic v2 strict frozen models.
* `Chunker` -- fixed-size + semantic-boundary chunkers.
* `EmbeddingService` Protocol + `DeterministicEmbeddingService` test stub.
* `VectorStore` Protocol; `InMemoryVectorStore` for tests; the real
  Qdrant adapter (requires the qdrant-client extra) lives in
  `loop_kb_engine.qdrant_store` and lands with S015b.
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
from loop_kb_engine.models import Chunk, Document
from loop_kb_engine.parsers import (
    DocumentParseError,
    Parser,
    ParserRegistry,
    TextParser,
    UnsupportedDocumentType,
    default_registry,
)
from loop_kb_engine.store import InMemoryVectorStore, VectorStore

__all__ = [
    "Chunk",
    "Chunker",
    "DeterministicEmbeddingService",
    "Document",
    "DocumentParseError",
    "EmbeddingService",
    "FixedSizeChunker",
    "HeadingChunker",
    "InMemoryVectorStore",
    "KnowledgeBase",
    "Parser",
    "ParserRegistry",
    "RetrievalResult",
    "SemanticChunker",
    "TextParser",
    "UnsupportedDocumentType",
    "VectorStore",
    "default_registry",
]

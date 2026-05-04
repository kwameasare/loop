"""Workspace KB document registry (P0.4).

cp-api owns the *metadata* — document id, source URL, title,
ingestion state, last_refreshed_at — while the kb-engine package
owns the actual chunks + vectors. The studio's "Knowledge Base"
tab uses these routes to list documents, kick off a re-crawl, and
delete a document (which cascades to kb-engine asynchronously).

In production wiring, ``refresh()`` enqueues a job onto kb-engine's
ingestion queue; the studio polls until ``state`` becomes
``ready`` (or ``failed``).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class KbDocumentState(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    READY = "ready"
    FAILED = "failed"


class KbDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    source_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=512)
    state: KbDocumentState
    chunk_count: int = Field(default=0, ge=0)
    created_at: datetime
    last_refreshed_at: datetime | None = None
    failure_reason: str | None = None


class KbDocumentCreate(BaseModel):
    """Body for POST /v1/workspaces/{id}/kb/documents."""

    model_config = ConfigDict(extra="forbid")
    source_url: AnyHttpUrl
    title: str = Field(default="", max_length=512)


class KbError(ValueError):
    """Raised on duplicate URLs, unknown ids, or invalid transitions."""


class KbDocumentService:
    """In-memory registry. Production wires this to a Postgres-backed
    store + an async job queue feeding kb-engine."""

    def __init__(self) -> None:
        self._docs: dict[UUID, KbDocument] = {}
        self._lock = asyncio.Lock()

    async def list_for_workspace(self, workspace_id: UUID) -> list[KbDocument]:
        async with self._lock:
            rows = [d for d in self._docs.values() if d.workspace_id == workspace_id]
            rows.sort(key=lambda d: d.created_at, reverse=True)
            return rows

    async def get(self, *, workspace_id: UUID, document_id: UUID) -> KbDocument:
        async with self._lock:
            doc = self._docs.get(document_id)
            if doc is None or doc.workspace_id != workspace_id:
                raise KbError(f"unknown document: {document_id}")
            return doc

    async def create(
        self, *, workspace_id: UUID, body: KbDocumentCreate
    ) -> KbDocument:
        async with self._lock:
            url = str(body.source_url)
            existing = next(
                (
                    d
                    for d in self._docs.values()
                    if d.workspace_id == workspace_id and d.source_url == url
                ),
                None,
            )
            if existing is not None:
                # Idempotent: posting a URL twice returns the existing
                # document rather than creating a dupe.
                return existing
            doc = KbDocument(
                id=uuid4(),
                workspace_id=workspace_id,
                source_url=url,
                title=body.title,
                state=KbDocumentState.PENDING,
                created_at=datetime.now(UTC),
            )
            self._docs[doc.id] = doc
            return doc

    async def delete(self, *, workspace_id: UUID, document_id: UUID) -> None:
        async with self._lock:
            doc = self._docs.get(document_id)
            if doc is None or doc.workspace_id != workspace_id:
                raise KbError(f"unknown document: {document_id}")
            del self._docs[document_id]

    async def refresh(
        self, *, workspace_id: UUID, document_id: UUID
    ) -> KbDocument:
        """Mark a document for re-ingestion. Idempotent."""
        async with self._lock:
            doc = self._docs.get(document_id)
            if doc is None or doc.workspace_id != workspace_id:
                raise KbError(f"unknown document: {document_id}")
            updated = doc.model_copy(
                update={
                    "state": KbDocumentState.INGESTING,
                    "last_refreshed_at": datetime.now(UTC),
                    "failure_reason": None,
                }
            )
            self._docs[document_id] = updated
            return updated

    async def refresh_all(self, workspace_id: UUID) -> list[KbDocument]:
        """Re-ingest every document in the workspace."""
        async with self._lock:
            now = datetime.now(UTC)
            updated_rows: list[KbDocument] = []
            for doc_id, doc in list(self._docs.items()):
                if doc.workspace_id != workspace_id:
                    continue
                updated = doc.model_copy(
                    update={
                        "state": KbDocumentState.INGESTING,
                        "last_refreshed_at": now,
                        "failure_reason": None,
                    }
                )
                self._docs[doc_id] = updated
                updated_rows.append(updated)
            return updated_rows


def serialise_doc(d: KbDocument) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "source_url": d.source_url,
        "title": d.title,
        "state": d.state.value,
        "chunk_count": d.chunk_count,
        "created_at": d.created_at.isoformat(),
        "last_refreshed_at": (
            d.last_refreshed_at.isoformat() if d.last_refreshed_at else None
        ),
        "failure_reason": d.failure_reason,
    }


__all__ = [
    "KbDocument",
    "KbDocumentCreate",
    "KbDocumentService",
    "KbDocumentState",
    "KbError",
    "serialise_doc",
]

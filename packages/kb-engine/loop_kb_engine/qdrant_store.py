"""Qdrant REST-backed vector store for KB integration paths."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from loop_kb_engine.models import Chunk


class QdrantRestVectorStore:
    """Minimal Qdrant REST adapter matching ``VectorStore``.

    The production deployment can swap in qdrant-client later; this keeps the
    protocol path dependency-light while still exercising real Qdrant in tests.
    """

    def __init__(
        self,
        *,
        base_url: str,
        collection_name: str,
        vector_size: int,
        timeout_seconds: float = 5.0,
    ) -> None:
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must use http or https")
        self._base_url = base_url.rstrip("/")
        self._collection = quote(collection_name, safe="")
        self._vector_size = vector_size
        self._timeout = timeout_seconds

    async def ensure_collection(self) -> None:
        await self._request(
            "PUT",
            f"/collections/{self._collection}",
            {"vectors": {"size": self._vector_size, "distance": "Cosine"}},
        )

    async def upsert(
        self,
        *,
        workspace_id: UUID,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must align")
        points = []
        for chunk, vector in zip(chunks, embeddings, strict=True):
            if chunk.workspace_id != workspace_id:
                raise ValueError("chunk.workspace_id != workspace_id")
            points.append(
                {
                    "id": str(chunk.id),
                    "vector": vector,
                    "payload": _chunk_payload(chunk),
                }
            )
        await self._request(
            "PUT",
            f"/collections/{self._collection}/points?wait=true",
            {"points": points},
        )

    async def query(
        self,
        *,
        workspace_id: UUID,
        embedding: list[float],
        top_k: int,
    ) -> list[tuple[Chunk, float]]:
        if top_k <= 0:
            return []
        response = await self._request(
            "POST",
            f"/collections/{self._collection}/points/search",
            {
                "vector": embedding,
                "limit": top_k,
                "filter": _filter(workspace_id=workspace_id),
                "with_payload": True,
            },
        )
        hits = response.get("result", [])
        return [(_chunk_from_hit(hit), float(hit.get("score", 0.0))) for hit in hits]

    async def delete_document(self, *, workspace_id: UUID, document_id: UUID) -> int:
        count = await self._count(workspace_id=workspace_id, document_id=document_id)
        await self._request(
            "POST",
            f"/collections/{self._collection}/points/delete?wait=true",
            {"filter": _filter(workspace_id=workspace_id, document_id=document_id)},
        )
        return count

    async def _count(self, *, workspace_id: UUID, document_id: UUID) -> int:
        response = await self._request(
            "POST",
            f"/collections/{self._collection}/points/count",
            {
                "exact": True,
                "filter": _filter(workspace_id=workspace_id, document_id=document_id),
            },
        )
        result = response.get("result", {})
        return int(result.get("count", 0)) if isinstance(result, dict) else 0

    async def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._request_sync, method, path, body)

    def _request_sync(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode()
        request = Request(  # noqa: S310 - base_url scheme is validated at construction.
            f"{self._base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                return json.loads(response.read().decode())
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RuntimeError(f"qdrant {method} {path} failed: {exc.code} {detail}") from exc


def qdrant_collection_name(*, workspace_id: UUID, kb_id: UUID) -> str:
    workspace = str(workspace_id).replace("-", "")[:8]
    kb = str(kb_id).replace("-", "")[:8]
    return f"kb_{workspace}_{kb}"


def _filter(*, workspace_id: UUID, document_id: UUID | None = None) -> dict[str, Any]:
    must: list[dict[str, Any]] = [
        {"key": "workspace_id", "match": {"value": str(workspace_id)}}
    ]
    if document_id is not None:
        must.append({"key": "document_id", "match": {"value": str(document_id)}})
    return {"must": must}


def _chunk_payload(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "workspace_id": str(chunk.workspace_id),
        "ordinal": chunk.ordinal,
        "text": chunk.text,
        "metadata": dict(chunk.metadata),
    }


def _chunk_from_hit(hit: dict[str, Any]) -> Chunk:
    payload = hit.get("payload", {})
    if not isinstance(payload, dict):
        raise RuntimeError("qdrant hit missing payload")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return Chunk(
        id=UUID(str(payload["chunk_id"])),
        document_id=UUID(str(payload["document_id"])),
        workspace_id=UUID(str(payload["workspace_id"])),
        ordinal=int(payload["ordinal"]),
        text=str(payload["text"]),
        metadata={str(k): str(v) for k, v in metadata.items()},
    )


__all__ = ["QdrantRestVectorStore", "qdrant_collection_name"]

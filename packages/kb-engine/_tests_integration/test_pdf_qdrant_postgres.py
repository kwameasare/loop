from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from importlib.resources import files
from pathlib import Path
from urllib.request import urlopen
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from loop_kb_engine import (
    DeterministicEmbeddingService,
    KnowledgeBase,
    QdrantRestVectorStore,
    SemanticChunker,
    qdrant_collection_name,
)
from loop_kb_engine.parsers_pdf import PdfBackend, PdfPage, PdfParser
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from testcontainers.core.container import DockerContainer
from testcontainers.postgres import PostgresContainer

pytestmark = pytest.mark.integration

DP_KB_REVISION = "dp_0002_kb"
APP_DB_USER = "loop_kb_app"
APP_DB_PASSWORD = "loop_kb_app"
PDF_BYTES = b"%PDF-1.4\n% Loop S213 fixture\n"
SOURCE_URI = "s3://loop-fixtures/support-policy.pdf"


class FixturePdfBackend(PdfBackend):
    def extract(self, data: bytes) -> tuple[tuple[PdfPage, ...], dict[str, str]]:
        assert data.startswith(b"%PDF-")
        return (
            (
                PdfPage(
                    page_no=1,
                    text=(
                        "Loop Enterprise support policy.\n\n"
                        "The Enterprise plan includes a 30 day refund window "
                        "for onboarding mistakes."
                    ),
                ),
            ),
            {"author": "loop-tests"},
        )


@pytest.fixture(scope="session")
def qdrant_url() -> Iterator[str]:
    with DockerContainer("qdrant/qdrant:v1.9.7").with_exposed_ports(6333) as container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(6333)}"
        _wait_for_qdrant(url)
        yield url


@pytest.fixture(scope="session")
def kb_postgres_engine() -> Iterator[Engine]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        url = postgres.get_connection_url()
        command.upgrade(_migration_config(url), DP_KB_REVISION)

        admin_engine = create_engine(url)
        with admin_engine.begin() as conn:
            conn.execute(text(f"CREATE ROLE {APP_DB_USER} LOGIN PASSWORD '{APP_DB_PASSWORD}'"))
            conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {APP_DB_USER}"))
            conn.execute(
                text(
                    f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
                    f"TO {APP_DB_USER}"
                )
            )
        admin_engine.dispose()

        app_url = make_url(url).set(username=APP_DB_USER, password=APP_DB_PASSWORD)
        engine = create_engine(app_url)
        try:
            yield engine
        finally:
            engine.dispose()


@pytest.mark.asyncio
async def test_pdf_upload_question_answer_cites_qdrant_and_postgres(
    qdrant_url: str, kb_postgres_engine: Engine
) -> None:
    workspace_id = uuid4()
    agent_id = uuid4()
    kb_id = uuid4()
    embedder = DeterministicEmbeddingService(dimensions=32)
    store = QdrantRestVectorStore(
        base_url=qdrant_url,
        collection_name=qdrant_collection_name(workspace_id=workspace_id, kb_id=kb_id),
        vector_size=embedder.dimensions,
    )
    await store.ensure_collection()

    document = PdfParser(backend=FixturePdfBackend()).parse(
        PDF_BYTES,
        workspace_id=workspace_id,
        title="Support policy",
        source=SOURCE_URI,
    )
    ingest_kb = KnowledgeBase(
        chunker=SemanticChunker(max_chars=500),
        embedder=embedder,
        vector_store=store,
    )
    chunks = await ingest_kb.ingest(document)
    assert len(chunks) == 1
    assert chunks[0].metadata["source_uri"] == SOURCE_URI
    assert int(chunks[0].metadata["byte_end"]) > int(chunks[0].metadata["byte_start"])

    _record_ingest_metadata(
        kb_postgres_engine,
        workspace_id=workspace_id,
        agent_id=agent_id,
        document_id=document.id,
        chunks=chunks,
    )

    query_kb = KnowledgeBase(embedder=embedder, vector_store=store)
    results = await query_kb.retrieve(
        workspace_id=workspace_id,
        query="What refund window does the Enterprise plan include?",
        top_k=1,
        alpha=0.0,
    )
    assert results

    answer = _answer_from_results(results)
    assert "30 day refund window" in answer
    assert SOURCE_URI in answer

    with kb_postgres_engine.begin() as conn:
        _set_workspace(conn, workspace_id)
        stored_source = conn.scalar(
            text("SELECT source_uri FROM kb_documents WHERE id = :document_id"),
            {"document_id": document.id},
        )
        stored_chunks = conn.scalar(text("SELECT count(*) FROM kb_chunks"))

        _set_workspace(conn, uuid4())
        cross_tenant_count = conn.scalar(text("SELECT count(*) FROM kb_documents"))

    assert stored_source == SOURCE_URI
    assert stored_chunks == 1
    assert cross_tenant_count == 0


def _migration_config(url: str) -> Config:
    ini_path = Path(str(files("loop_data_plane.migrations").joinpath("alembic.ini")))
    cfg = Config(file_=str(ini_path), ini_section="alembic")
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.set_main_option("version_table", "alembic_version_dp")
    return cfg


def _wait_for_qdrant(base_url: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/collections", timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("qdrant container did not become ready")


def _record_ingest_metadata(
    engine: Engine,
    *,
    workspace_id: UUID,
    agent_id: UUID,
    document_id: UUID,
    chunks: list[object],
) -> None:
    with engine.begin() as conn:
        _set_workspace(conn, workspace_id)
        conn.execute(
            text(
                """
                INSERT INTO kb_documents (
                    id, workspace_id, agent_id, source_uri, mime_type, byte_size,
                    content_hash, title, metadata
                )
                VALUES (
                    :id, :workspace_id, :agent_id, :source_uri, 'application/pdf',
                    :byte_size, :content_hash, 'Support policy', CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "id": document_id,
                "workspace_id": workspace_id,
                "agent_id": agent_id,
                "source_uri": SOURCE_URI,
                "byte_size": len(PDF_BYTES),
                "content_hash": hashlib.sha256(PDF_BYTES).hexdigest(),
                "metadata": json.dumps({"page_count": "1"}),
            },
        )
        for chunk in chunks:
            conn.execute(
                text(
                    """
                    INSERT INTO kb_chunks (
                        id, workspace_id, agent_id, document_id, ordinal, content,
                        content_hash, token_count, metadata, embedded_at
                    )
                    VALUES (
                        :id, :workspace_id, :agent_id, :document_id, :ordinal,
                        :content, :content_hash, :token_count, CAST(:metadata AS jsonb),
                        now()
                    )
                    """
                ),
                {
                    "id": chunk.id,
                    "workspace_id": workspace_id,
                    "agent_id": agent_id,
                    "document_id": document_id,
                    "ordinal": chunk.ordinal,
                    "content": chunk.text,
                    "content_hash": hashlib.sha256(chunk.text.encode()).hexdigest(),
                    "token_count": len(chunk.text.split()),
                    "metadata": json.dumps(chunk.metadata),
                },
            )


def _set_workspace(conn: object, workspace_id: UUID) -> None:
    conn.execute(
        text("SELECT set_config('loop.workspace_id', :workspace_id, true)"),
        {"workspace_id": str(workspace_id)},
    )


def _answer_from_results(results: object) -> str:
    top = results[0]
    source = top.chunk.metadata["source_uri"]
    return f"{top.chunk.text}\n\nSources: {source}"

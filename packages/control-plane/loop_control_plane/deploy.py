"""Deploy controller v0.

A deploy moves a built artifact (a pinned snapshot of an agent
config + workflow + skills + image tag) through a small state
machine: PENDING -> BUILDING -> PUSHING -> APPLYING -> READY, with
FAILED / ROLLED_BACK as terminals.

Real deployments hit a container registry and a Kubernetes API. To
keep the controller testable, the registry and kube client live
behind Protocols and ship with in-memory fakes. The controller has
zero direct dependency on docker, kubernetes, or the network.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DeployPhase(StrEnum):
    PENDING = "pending"
    BUILDING = "building"
    PUSHING = "pushing"
    APPLYING = "applying"
    READY = "ready"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


TERMINAL_PHASES = frozenset({DeployPhase.READY, DeployPhase.FAILED, DeployPhase.ROLLED_BACK})


class DeployArtifact(BaseModel):
    """Immutable snapshot the controller is asked to deploy."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    workspace_id: UUID
    agent_id: UUID
    version: str = Field(min_length=1, max_length=64)
    source_digest: str = Field(min_length=8)


class BuildResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    image_ref: str = Field(min_length=1)
    digest: str = Field(min_length=8)


class Deploy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    artifact: DeployArtifact
    phase: DeployPhase
    started_at: datetime
    updated_at: datetime
    image_ref: str | None = None
    error: str | None = None


class DeployError(RuntimeError):
    """Raised by builders / registries / kube clients to fail a deploy."""


class ImageBuilder(Protocol):
    async def build(self, artifact: DeployArtifact) -> BuildResult: ...


class ImageRegistry(Protocol):
    async def push(self, build: BuildResult) -> str:
        """Return the canonical pullable image ref."""


class KubeClient(Protocol):
    async def apply(self, *, deploy_id: UUID, image_ref: str) -> None: ...
    async def rollback(self, deploy_id: UUID) -> None: ...


# ----------------------------------------------------------- in-memory fakes


class InMemoryImageBuilder:
    def __init__(
        self,
        *,
        on_build: Callable[[DeployArtifact], Awaitable[None]] | None = None,
    ) -> None:
        self._on_build = on_build
        self.builds: list[DeployArtifact] = []

    async def build(self, artifact: DeployArtifact) -> BuildResult:
        if self._on_build is not None:
            await self._on_build(artifact)
        self.builds.append(artifact)
        return BuildResult(
            image_ref=f"local/loop/{artifact.workspace_id}:{artifact.version}",
            digest=f"sha256:{artifact.source_digest[:64]:0<64}",
        )


class InMemoryImageRegistry:
    def __init__(self) -> None:
        self.pushed: list[BuildResult] = []

    async def push(self, build: BuildResult) -> str:
        self.pushed.append(build)
        return f"registry.loop.test/{build.image_ref}@{build.digest}"


class InMemoryKubeClient:
    def __init__(
        self,
        *,
        on_apply: Callable[[UUID, str], Awaitable[None]] | None = None,
    ) -> None:
        self._on_apply = on_apply
        self.applied: list[tuple[UUID, str]] = []
        self.rolled_back: list[UUID] = []

    async def apply(self, *, deploy_id: UUID, image_ref: str) -> None:
        if self._on_apply is not None:
            await self._on_apply(deploy_id, image_ref)
        self.applied.append((deploy_id, image_ref))

    async def rollback(self, deploy_id: UUID) -> None:
        self.rolled_back.append(deploy_id)


# ------------------------------------------------------------------ controller


class DeployController:
    """Orchestrates one deploy at a time per `(workspace, agent)`.

    Concurrency is bounded by an asyncio.Lock on writes; a deploy
    flowing through the state machine is single-threaded inside the
    controller, while readers (`get`) take the same lock briefly.
    """

    def __init__(
        self,
        *,
        builder: ImageBuilder,
        registry: ImageRegistry,
        kube: KubeClient,
    ) -> None:
        self._builder = builder
        self._registry = registry
        self._kube = kube
        self._deploys: dict[UUID, Deploy] = {}
        self._lock = asyncio.Lock()

    async def submit(self, artifact: DeployArtifact) -> Deploy:
        now = datetime.now(UTC)
        deploy = Deploy(
            id=uuid4(),
            artifact=artifact,
            phase=DeployPhase.PENDING,
            started_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._deploys[deploy.id] = deploy
        return deploy

    async def get(self, deploy_id: UUID) -> Deploy:
        async with self._lock:
            d = self._deploys.get(deploy_id)
            if d is None:
                raise DeployError(f"unknown deploy: {deploy_id}")
            return d

    async def run(self, deploy_id: UUID) -> Deploy:
        """Drive ``deploy_id`` through the state machine.

        Idempotent on terminal phases: returns the stored record.
        """
        deploy = await self.get(deploy_id)
        if deploy.phase in TERMINAL_PHASES:
            return deploy

        try:
            deploy = await self._advance(deploy, DeployPhase.BUILDING)
            built = await self._builder.build(deploy.artifact)

            deploy = await self._advance(deploy, DeployPhase.PUSHING)
            image_ref = await self._registry.push(built)

            deploy = await self._advance(deploy, DeployPhase.APPLYING, image_ref=image_ref)
            await self._kube.apply(deploy_id=deploy.id, image_ref=image_ref)

            deploy = await self._advance(deploy, DeployPhase.READY)
        except Exception as exc:
            deploy = await self._advance(
                deploy, DeployPhase.FAILED, error=f"{type(exc).__name__}: {exc}"
            )
        return deploy

    async def rollback(self, deploy_id: UUID) -> Deploy:
        deploy = await self.get(deploy_id)
        if deploy.phase is DeployPhase.ROLLED_BACK:
            return deploy
        if deploy.phase is DeployPhase.PENDING:
            raise DeployError("cannot roll back a PENDING deploy")
        await self._kube.rollback(deploy.id)
        return await self._advance(deploy, DeployPhase.ROLLED_BACK)

    async def _advance(
        self,
        deploy: Deploy,
        phase: DeployPhase,
        *,
        image_ref: str | None = None,
        error: str | None = None,
    ) -> Deploy:
        update: dict[str, object] = {
            "phase": phase,
            "updated_at": datetime.now(UTC),
        }
        if image_ref is not None:
            update["image_ref"] = image_ref
        if error is not None:
            update["error"] = error
        async with self._lock:
            new = deploy.model_copy(update=update)
            self._deploys[deploy.id] = new
            return new


__all__ = [
    "TERMINAL_PHASES",
    "BuildResult",
    "Deploy",
    "DeployArtifact",
    "DeployController",
    "DeployError",
    "DeployPhase",
    "ImageBuilder",
    "ImageRegistry",
    "InMemoryImageBuilder",
    "InMemoryImageRegistry",
    "InMemoryKubeClient",
    "KubeClient",
]

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

from loop_control_plane.slsa_provenance import (
    ProvenanceError,
    ProvenancePolicy,
    ProvenanceVerifier,
)


class DeployPhase(StrEnum):
    PENDING = "pending"
    BUILDING = "building"
    EVALUATING = "evaluating"
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


class EvalReport(BaseModel):
    """Outcome of a candidate-vs-baseline regression run.

    ``baseline_pass_rate`` is ``None`` for the very first deploy of an
    agent (no prior baseline exists). ``regression`` is true iff a
    baseline exists and ``pass_rate < baseline_pass_rate``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    pass_rate: float = Field(ge=0.0, le=1.0)
    total_cases: int = Field(ge=0)
    baseline_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    regression: bool = False


class Deploy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    id: UUID
    artifact: DeployArtifact
    phase: DeployPhase
    started_at: datetime
    updated_at: datetime
    image_ref: str | None = None
    error: str | None = None
    eval_report: EvalReport | None = None


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


class EvalGate(Protocol):
    """Runs a regression eval suite against a candidate artifact.

    Implementations call into ``loop_eval`` (or any harness) and
    return an :class:`EvalReport` whose ``regression`` flag drives
    deploy gating. The gate MUST set ``regression=True`` whenever a
    baseline is provided and the candidate's ``pass_rate`` is
    strictly lower than that baseline.
    """

    async def evaluate(
        self,
        artifact: DeployArtifact,
        *,
        baseline_pass_rate: float | None,
    ) -> EvalReport: ...


class BaselineRegistry(Protocol):
    """Stores the most recent passing eval pass_rate per agent.

    The controller reads via :meth:`get` before evaluating a
    candidate and writes via :meth:`record` only after a deploy
    reaches READY -- so a failed candidate never poisons the
    baseline.
    """

    async def get(self, *, workspace_id: UUID, agent_id: UUID) -> float | None: ...

    async def record(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        pass_rate: float,
    ) -> None: ...


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


class InMemoryEvalGate:
    """Test fake: returns a queued sequence of ``pass_rate`` values.

    Each call pops the next configured pass_rate; ``regression`` is
    derived against the supplied baseline.
    """

    def __init__(self, *, pass_rates: list[float], total_cases: int = 10) -> None:
        self._pass_rates = list(pass_rates)
        self._total_cases = total_cases
        self.calls: list[tuple[DeployArtifact, float | None]] = []

    async def evaluate(
        self,
        artifact: DeployArtifact,
        *,
        baseline_pass_rate: float | None,
    ) -> EvalReport:
        if not self._pass_rates:
            raise DeployError("InMemoryEvalGate: no more pass_rates queued")
        pr = self._pass_rates.pop(0)
        self.calls.append((artifact, baseline_pass_rate))
        regression = baseline_pass_rate is not None and pr < baseline_pass_rate
        return EvalReport(
            pass_rate=pr,
            total_cases=self._total_cases,
            baseline_pass_rate=baseline_pass_rate,
            regression=regression,
        )


class InMemoryBaselineRegistry:
    def __init__(self) -> None:
        self._values: dict[tuple[UUID, UUID], float] = {}
        self.records: list[tuple[UUID, UUID, float]] = []

    async def get(self, *, workspace_id: UUID, agent_id: UUID) -> float | None:
        return self._values.get((workspace_id, agent_id))

    async def record(
        self,
        *,
        workspace_id: UUID,
        agent_id: UUID,
        pass_rate: float,
    ) -> None:
        self._values[(workspace_id, agent_id)] = pass_rate
        self.records.append((workspace_id, agent_id, pass_rate))


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
        eval_gate: EvalGate | None = None,
        baselines: BaselineRegistry | None = None,
        provenance_verifier: ProvenanceVerifier | None = None,
        provenance_policy: ProvenancePolicy | None = None,
    ) -> None:
        if (eval_gate is None) != (baselines is None):
            raise DeployError("eval_gate and baselines must be provided together")
        if provenance_verifier is not None and provenance_policy is None:
            provenance_policy = ProvenancePolicy()
        self._builder = builder
        self._registry = registry
        self._kube = kube
        self._eval_gate = eval_gate
        self._baselines = baselines
        self._provenance_verifier = provenance_verifier
        self._provenance_policy = provenance_policy
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

            report: EvalReport | None = None
            if self._eval_gate is not None and self._baselines is not None:
                deploy = await self._advance(deploy, DeployPhase.EVALUATING)
                baseline = await self._baselines.get(
                    workspace_id=deploy.artifact.workspace_id,
                    agent_id=deploy.artifact.agent_id,
                )
                report = await self._eval_gate.evaluate(
                    deploy.artifact, baseline_pass_rate=baseline
                )
                deploy = await self._advance(deploy, DeployPhase.EVALUATING, eval_report=report)
                if report.regression:
                    raise DeployError(
                        f"eval-regression: pass_rate {report.pass_rate:.4f} "
                        f"< baseline {baseline:.4f}"  # type: ignore[str-bytes-safe]
                    )

            deploy = await self._advance(deploy, DeployPhase.PUSHING)

            # SLSA Level-3 provenance gate: verify before pushing to registry.
            if self._provenance_verifier is not None:
                assert self._provenance_policy is not None
                try:
                    self._provenance_verifier.verify(built.digest, self._provenance_policy)
                except ProvenanceError as exc:
                    raise DeployError(f"provenance-gate: {exc}") from exc

            image_ref = await self._registry.push(built)

            deploy = await self._advance(deploy, DeployPhase.APPLYING, image_ref=image_ref)
            await self._kube.apply(deploy_id=deploy.id, image_ref=image_ref)

            deploy = await self._advance(deploy, DeployPhase.READY)
            if self._baselines is not None and report is not None and not report.regression:
                await self._baselines.record(
                    workspace_id=deploy.artifact.workspace_id,
                    agent_id=deploy.artifact.agent_id,
                    pass_rate=report.pass_rate,
                )
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
        eval_report: EvalReport | None = None,
    ) -> Deploy:
        update: dict[str, object] = {
            "phase": phase,
            "updated_at": datetime.now(UTC),
        }
        if image_ref is not None:
            update["image_ref"] = image_ref
        if error is not None:
            update["error"] = error
        if eval_report is not None:
            update["eval_report"] = eval_report
        async with self._lock:
            new = deploy.model_copy(update=update)
            self._deploys[deploy.id] = new
            return new


__all__ = [
    "TERMINAL_PHASES",
    "BaselineRegistry",
    "BuildResult",
    "Deploy",
    "DeployArtifact",
    "DeployController",
    "DeployError",
    "DeployPhase",
    "EvalGate",
    "EvalReport",
    "ImageBuilder",
    "ImageRegistry",
    "InMemoryBaselineRegistry",
    "InMemoryEvalGate",
    "InMemoryImageBuilder",
    "InMemoryImageRegistry",
    "InMemoryKubeClient",
    "KubeClient",
]

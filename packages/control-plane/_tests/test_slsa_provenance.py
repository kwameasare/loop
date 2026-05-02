"""Tests for SLSA Level-3 build-provenance gate — S802."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_control_plane import (
    DeployArtifact,
    DeployController,
    DeployPhase,
    InMemoryImageBuilder,
    InMemoryImageRegistry,
    InMemoryKubeClient,
    InMemoryProvenanceStore,
    ProvenanceError,
    ProvenancePolicy,
    SlsaProvenance,
    StubProvenanceVerifier,
)

_TRUSTED_BUILDER = (
    "https://github.com/slsa-framework/slsa-github-generator/"
    ".github/workflows/generator_container_slsa3.yml@refs/tags/v1.9.0"
)
_UNTRUSTED_BUILDER = "https://attacker.example/evil-builder"
_POLICY = ProvenancePolicy(trusted_builder_ids=frozenset({"https://github.com/slsa-framework/"}))


def _artifact() -> DeployArtifact:
    return DeployArtifact(
        id=uuid4(),
        workspace_id=uuid4(),
        agent_id=uuid4(),
        version="2.0.0",
        source_digest="deadbeef01234567",
    )


def _provenance(digest: str, *, builder_id: str = _TRUSTED_BUILDER) -> SlsaProvenance:
    return SlsaProvenance(
        subject_digest=digest,
        builder_id=builder_id,
        build_type="https://slsa.dev/provenance/v0.2",
        materials=[{"uri": "git+https://github.com/loop/loop", "digest": {"sha1": "abc"}}],
    )


# ---------------------------------------------------------------------------
# SlsaProvenance model
# ---------------------------------------------------------------------------


def test_provenance_fields_are_accessible() -> None:
    prov = _provenance("sha256:aabbcc")
    assert prov.subject_digest == "sha256:aabbcc"
    assert prov.builder_id == _TRUSTED_BUILDER
    assert prov.build_type == "https://slsa.dev/provenance/v0.2"
    assert prov.materials[0]["uri"] == "git+https://github.com/loop/loop"


def test_provenance_is_immutable() -> None:
    prov = _provenance("sha256:aabbcc")
    with pytest.raises((AttributeError, TypeError)):
        prov.subject_digest = "sha256:mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ProvenancePolicy
# ---------------------------------------------------------------------------


def test_policy_trusts_matching_builder_prefix() -> None:
    assert _POLICY.is_trusted_builder(_TRUSTED_BUILDER)


def test_policy_rejects_untrusted_builder() -> None:
    assert not _POLICY.is_trusted_builder(_UNTRUSTED_BUILDER)


def test_default_policy_trusts_slsa_github_generator_and_tekton() -> None:
    policy = ProvenancePolicy()
    assert policy.is_trusted_builder(
        "https://github.com/slsa-framework/slsa-github-generator/"
        ".github/workflows/generator_container_slsa3.yml@refs/tags/v1.0.0"
    )
    assert policy.is_trusted_builder("https://tekton.loop.internal/pipelines/build")
    assert not policy.is_trusted_builder("https://evil.example/build")


# ---------------------------------------------------------------------------
# StubProvenanceVerifier
# ---------------------------------------------------------------------------


def test_stub_verifier_returns_provenance_when_registered() -> None:
    store = InMemoryProvenanceStore()
    digest = "sha256:cafebabe0011"
    store.register(_provenance(digest))
    verifier = StubProvenanceVerifier(store)
    prov = verifier.verify(digest, _POLICY)
    assert prov.subject_digest == digest


def test_stub_verifier_raises_when_digest_not_registered() -> None:
    store = InMemoryProvenanceStore()
    verifier = StubProvenanceVerifier(store)
    with pytest.raises(ProvenanceError, match="no SLSA provenance"):
        verifier.verify("sha256:unknown", _POLICY)


def test_stub_verifier_raises_when_builder_untrusted() -> None:
    store = InMemoryProvenanceStore()
    digest = "sha256:deadbeef9999"
    store.register(_provenance(digest, builder_id=_UNTRUSTED_BUILDER))
    verifier = StubProvenanceVerifier(store)
    with pytest.raises(ProvenanceError, match="not in the trusted builder set"):
        verifier.verify(digest, _POLICY)


# ---------------------------------------------------------------------------
# Deploy gate integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deploy_succeeds_when_slsa3_provenance_present() -> None:
    builder = InMemoryImageBuilder()
    store = InMemoryProvenanceStore()
    kube = InMemoryKubeClient()

    artifact = _artifact()
    # Pre-register provenance for the digest InMemoryImageBuilder will produce.
    expected_digest = f"sha256:{artifact.source_digest[:64]:0<64}"
    store.register(_provenance(expected_digest))

    ctl = DeployController(
        builder=builder,
        registry=InMemoryImageRegistry(),
        kube=kube,
        provenance_verifier=StubProvenanceVerifier(store),
        provenance_policy=_POLICY,
    )
    deploy = await ctl.submit(artifact)
    final = await ctl.run(deploy.id)

    assert final.phase is DeployPhase.READY
    assert len(kube.applied) == 1


@pytest.mark.asyncio
async def test_deploy_fails_when_provenance_missing() -> None:
    store = InMemoryProvenanceStore()  # empty — no provenance registered

    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
        provenance_verifier=StubProvenanceVerifier(store),
        provenance_policy=_POLICY,
    )
    deploy = await ctl.submit(_artifact())
    final = await ctl.run(deploy.id)

    assert final.phase is DeployPhase.FAILED
    assert final.error is not None
    assert "provenance-gate" in final.error


@pytest.mark.asyncio
async def test_deploy_fails_when_builder_untrusted() -> None:
    artifact = _artifact()
    expected_digest = f"sha256:{artifact.source_digest[:64]:0<64}"
    store = InMemoryProvenanceStore()
    store.register(_provenance(expected_digest, builder_id=_UNTRUSTED_BUILDER))

    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
        provenance_verifier=StubProvenanceVerifier(store),
        provenance_policy=_POLICY,
    )
    deploy = await ctl.submit(artifact)
    final = await ctl.run(deploy.id)

    assert final.phase is DeployPhase.FAILED
    assert final.error is not None
    assert "provenance-gate" in final.error


@pytest.mark.asyncio
async def test_deploy_without_verifier_still_succeeds() -> None:
    """When no verifier is injected the gate is skipped (opt-in)."""
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
    )
    deploy = await ctl.submit(_artifact())
    final = await ctl.run(deploy.id)
    assert final.phase is DeployPhase.READY


@pytest.mark.asyncio
async def test_deploy_defaults_policy_when_only_verifier_provided() -> None:
    """Omitting provenance_policy should use the default ProvenancePolicy."""
    artifact = _artifact()
    expected_digest = f"sha256:{artifact.source_digest[:64]:0<64}"
    store = InMemoryProvenanceStore()
    # Use a builder_id trusted by the default policy.
    store.register(
        _provenance(
            expected_digest,
            builder_id=(
                "https://github.com/slsa-framework/slsa-github-generator/"
                ".github/workflows/generator_container_slsa3.yml@refs/tags/v1.9.0"
            ),
        )
    )
    ctl = DeployController(
        builder=InMemoryImageBuilder(),
        registry=InMemoryImageRegistry(),
        kube=InMemoryKubeClient(),
        provenance_verifier=StubProvenanceVerifier(store),
        # provenance_policy omitted — controller defaults to ProvenancePolicy()
    )
    deploy = await ctl.submit(artifact)
    final = await ctl.run(deploy.id)
    assert final.phase is DeployPhase.READY

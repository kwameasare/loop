"""Pass13 tests for the MCP marketplace control-plane slice."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from loop_control_plane.mcp_marketplace import (
    CommunityPublishFlow,
    DuplicateReviewError,
    DuplicateVersionError,
    FirstPartyCatalog,
    InMemoryMarketplaceStore,
    MarketplaceAcceptanceGate,
    MarketplaceAnalytics,
    MarketplaceBrowser,
    MarketplaceInstaller,
    MarketplacePublisher,
    MarketplaceReviews,
    McpServerManifest,
    PublishResult,
    RejectedManifestError,
    ServerPublishCli,
    TrustedPublisherVerifier,
    compute_manifest_digest,
    first_party_manifests,
)


@dataclass
class FakeSigner:
    signed: list[str] = field(default_factory=list)

    def sign(self, payload_digest: str) -> str:
        self.signed.append(payload_digest)
        return f"sig:loop-maintainer:{payload_digest}"


@dataclass
class FakePublishClient:
    uploaded: list[McpServerManifest] = field(default_factory=list)

    def upload_manifest(self, manifest: McpServerManifest) -> str:
        self.uploaded.append(manifest)
        return f"registry/mcp/{manifest.slug}/{manifest.version}.json"


def _publisher(store: InMemoryMarketplaceStore) -> MarketplacePublisher:
    verifier = TrustedPublisherVerifier(trusted_publishers=("loop",))
    return MarketplacePublisher(store=store, verifier=verifier)


def _publish_catalog(store: InMemoryMarketplaceStore) -> tuple[PublishResult, ...]:
    return FirstPartyCatalog().publish_all(_publisher(store), now_ms=1000)


def _manifest(slug: str) -> McpServerManifest:
    for manifest in first_party_manifests():
        if manifest.slug == slug:
            return manifest
    raise AssertionError(f"missing manifest {slug}")


def _resign(manifest: McpServerManifest) -> McpServerManifest:
    digest = compute_manifest_digest(manifest)
    return manifest.model_copy(
        update={
            "manifest_digest": digest,
            "signature": f"sig:loop-maintainer:{digest}",
        }
    )


def test_signed_publish_rejects_bad_digest_and_duplicate_version() -> None:
    store = InMemoryMarketplaceStore()
    publisher = _publisher(store)
    manifest = _manifest("salesforce")
    result = publisher.publish(manifest, now_ms=1)
    assert result.verified is True
    assert result.quality_score > 0

    with pytest.raises(DuplicateVersionError):
        publisher.publish(manifest, now_ms=2)

    tampered = manifest.model_copy(update={"manifest_digest": "sha256:not-real"})
    with pytest.raises(RejectedManifestError):
        _publisher(InMemoryMarketplaceStore()).publish(tampered, now_ms=3)


def test_install_flow_pins_versions_and_surfaces_upgrade_state() -> None:
    store = InMemoryMarketplaceStore()
    publisher = _publisher(store)
    base = _manifest("gmail")
    publisher.publish(base, now_ms=1)
    v2 = _resign(base.model_copy(update={"version": "1.1.0"}))
    publisher.publish(v2, now_ms=2)

    installer = MarketplaceInstaller(store=store)
    install = installer.install(
        workspace_id="workspace-1",
        agent_id="agent-1",
        server_id=base.server_id,
        version="1.0.0",
        installed_by_sub="user-1",
        now_ms=3,
    )
    assert install.version == "1.0.0"

    installed = installer.installed_for_agent(workspace_id="workspace-1", agent_id="agent-1")
    assert installed[0].pinned_version == "1.0.0"
    assert installed[0].latest_version == "1.1.0"
    assert installed[0].upgrade_available is True
    assert "send_message" in installed[0].tools


def test_browse_filters_by_category_and_searches_tools() -> None:
    store = InMemoryMarketplaceStore()
    _publish_catalog(store)

    browser = MarketplaceBrowser(store=store)
    crm = browser.browse(category="crm")
    assert {item.slug for item in crm} >= {"salesforce", "hubspot-read", "hubspot-write"}

    results = browser.browse(query="refund")
    assert [item.slug for item in results] == ["stripe-write"]
    assert results[0].install_button_enabled is True
    assert results[0].quality_score > 0


def test_reviews_are_one_per_workspace_and_moderated_for_abuse() -> None:
    store = InMemoryMarketplaceStore()
    _publish_catalog(store)
    reviews = MarketplaceReviews(store=store)
    review = reviews.add_review(
        workspace_id="workspace-1",
        server_id=_manifest("notion").server_id,
        rating=5,
        body="Fast and useful for agent work.",
        now_ms=10,
    )
    assert review.moderation_required is False

    with pytest.raises(DuplicateReviewError):
        reviews.add_review(
            workspace_id="workspace-1",
            server_id=_manifest("notion").server_id,
            rating=4,
            body="Second review",
            now_ms=11,
        )

    flagged = reviews.add_review(
        workspace_id="workspace-2",
        server_id=_manifest("notion").server_id,
        rating=1,
        body="This reads like spam",
        now_ms=12,
    )
    assert flagged.moderation_required is True


def test_usage_analytics_counts_only_opted_in_calls() -> None:
    store = InMemoryMarketplaceStore()
    _publish_catalog(store)
    analytics = MarketplaceAnalytics(store=store)
    server_id = _manifest("web-search").server_id

    ignored = analytics.record_call(server_id=server_id, opt_in=False, now_ms=20)
    counted = analytics.record_call(server_id=server_id, opt_in=True, now_ms=21)

    assert ignored.calls == 0
    assert counted.calls == 1
    assert counted.last_called_at_ms == 21


def test_community_publish_flow_flags_unsigned_prs_for_maintainer_signature() -> None:
    verifier = TrustedPublisherVerifier(trusted_publishers=("loop",))
    flow = CommunityPublishFlow(verifier=verifier)
    manifest = _manifest("github")
    ready = flow.submit(manifest, contributor="ada")
    assert ready.ready_for_review is True
    assert ready.maintainer_signature_required is False
    assert ready.ci_checks == ("schema", "signature", "compatibility", "integration-test")

    community = manifest.model_copy(
        update={
            "publisher": "community",
            "signed_by": "unknown",
            "signature": "sig:unknown",
        }
    )
    community = community.model_copy(update={"manifest_digest": compute_manifest_digest(community)})
    blocked = flow.submit(community, contributor="ada")
    assert blocked.ready_for_review is False
    assert blocked.maintainer_signature_required is True


def test_first_party_catalog_covers_mvp_servers_and_acceptance_gate() -> None:
    manifests = first_party_manifests()
    assert len(manifests) >= 25
    by_slug = {manifest.slug: manifest for manifest in manifests}
    required = {
        "google-calendar": {"list_events", "create_event"},
        "gmail": {"search_messages", "create_draft", "send_message"},
        "github": {"create_issue", "comment_on_issue", "list_pull_requests"},
        "linear": {"list_issues", "create_issue", "update_issue", "list_projects"},
        "jira": {"list_issues", "create_issue", "add_comment"},
        "notion": {"query_database", "create_page"},
        "asana": {"list_projects", "create_task", "update_task"},
        "stripe-write": {"create_refund", "create_invoice"},
        "slack-write": {"post_message", "send_direct_message"},
        "hubspot-write": {"create_contact", "update_deal"},
        "web-search": {"tavily_search", "brave_search"},
    }
    for slug, tool_names in required.items():
        assert slug in by_slug
        assert {tool.name for tool in by_slug[slug].tools} >= tool_names

    store = InMemoryMarketplaceStore()
    _publish_catalog(store)
    ready = MarketplaceAcceptanceGate(store=store).assert_ready()
    assert len(ready) >= 25
    assert min(item.quality_score for item in ready) > 0


def test_server_publish_cli_signs_and_uploads_manifest() -> None:
    signer = FakeSigner()
    client = FakePublishClient()
    cli = ServerPublishCli(signer=signer, client=client)

    manifest = _manifest("slack-write").model_copy(update={"signature": "sig:pending"})
    result = cli.publish(manifest)

    assert signer.signed == [compute_manifest_digest(manifest)]
    assert client.uploaded[0].signature == f"sig:loop-maintainer:{signer.signed[0]}"
    assert result.registry_path == "registry/mcp/slack-write/1.0.0.json"

"""MCP marketplace registry, installs, quality, and first-party catalog.

The marketplace is intentionally pure and protocol-driven. Production callers
can back the store with Postgres, object storage, and cosign, while tests use
the in-memory store and deterministic signing helpers without touching the
network.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CommunityPublishFlow",
    "CommunityPublishResult",
    "DuplicateReviewError",
    "DuplicateVersionError",
    "FirstPartyCatalog",
    "InMemoryMarketplaceStore",
    "InstallNotFoundError",
    "InstalledToolView",
    "ManifestSignatureVerifier",
    "MarketplaceAcceptanceGate",
    "MarketplaceAnalytics",
    "MarketplaceBrowseItem",
    "MarketplaceBrowser",
    "MarketplaceError",
    "MarketplaceInstall",
    "MarketplaceInstaller",
    "MarketplacePublisher",
    "MarketplaceReview",
    "MarketplaceServer",
    "MarketplaceUsageAggregate",
    "McpServerManifest",
    "McpServerVersion",
    "McpToolSpec",
    "PublishClient",
    "PublishResult",
    "QualityBreakdown",
    "QualityScorer",
    "RejectedManifestError",
    "ServerNotFoundError",
    "ServerPublishCli",
    "SigningKey",
    "TrustedPublisherVerifier",
    "UnknownVersionError",
    "compute_manifest_digest",
    "first_party_manifests",
]


RiskKind = Literal["read", "write", "admin"]
AuthKind = Literal["oauth2", "api_key", "pat", "app", "none"]
InstallStatus = Literal["installed", "upgraded", "uninstalled"]


class McpToolSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    risk: RiskKind
    input_schema: Mapping[str, object] = Field(default_factory=dict)


class McpServerManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    name: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    description: str = Field(min_length=1)
    version: str = Field(min_length=1)
    categories: tuple[str, ...] = Field(min_length=1)
    capabilities: tuple[str, ...] = Field(default_factory=tuple)
    tools: tuple[McpToolSpec, ...] = Field(min_length=1)
    auth_type: AuthKind
    scopes: tuple[str, ...] = Field(default_factory=tuple)
    source_url: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)
    manifest_digest: str = Field(min_length=1)
    manifest_uri: str = Field(min_length=1)
    signature: str = Field(min_length=1)
    signed_by: str = Field(min_length=1)
    compatibility: tuple[str, ...] = Field(default=("loop>=0.1",))
    integration_test_green: bool = True


class MarketplaceServer(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    slug: str
    name: str
    publisher: str
    description: str
    categories: tuple[str, ...]
    created_at_ms: int = Field(ge=0)
    verified: bool
    signed_by: str
    latest_version: str


class McpServerVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    version: str
    manifest_digest: str
    image_digest: str
    manifest_uri: str
    signature: str
    tools: tuple[McpToolSpec, ...]
    scopes: tuple[str, ...]
    signed_by: str
    published_at_ms: int = Field(ge=0)
    verified: bool
    active: bool
    integration_test_green: bool
    quality_score: int = Field(ge=0, le=100)


class MarketplaceInstall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    installed_by_sub: str = Field(min_length=1)
    installed_at_ms: int = Field(ge=0)
    status: InstallStatus = "installed"


class InstalledToolView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: str
    agent_id: str
    server_id: str
    slug: str
    name: str
    pinned_version: str
    latest_version: str
    upgrade_available: bool
    tools: tuple[str, ...]
    uninstall_requires_confirm: bool = True


class MarketplaceReview(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    workspace_id: str = Field(min_length=1)
    server_id: str = Field(min_length=1)
    rating: int = Field(ge=1, le=5)
    body: str = Field(min_length=1)
    created_at_ms: int = Field(ge=0)
    moderation_required: bool = False


class MarketplaceUsageAggregate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    installs: int = Field(ge=0)
    calls: int = Field(ge=0)
    last_called_at_ms: int | None = Field(default=None, ge=0)


class QualityBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    score: int = Field(ge=0, le=100)
    compatibility: int = Field(ge=0, le=25)
    signed_manifest: int = Field(ge=0, le=25)
    rating: int = Field(ge=0, le=25)
    usage: int = Field(ge=0, le=15)
    test_health: int = Field(ge=0, le=10)


class MarketplaceBrowseItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    slug: str
    name: str
    publisher: str
    description: str
    categories: tuple[str, ...]
    latest_version: str
    quality_score: int = Field(ge=0, le=100)
    average_rating: float = Field(ge=0.0, le=5.0)
    installs: int = Field(ge=0)
    calls: int = Field(ge=0)
    install_button_enabled: bool


class PublishResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    version: str
    verified: bool
    registry_path: str
    quality_score: int = Field(ge=0, le=100)


class CommunityPublishResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    server_id: str
    version: str
    pull_request_path: str
    ci_checks: tuple[str, ...]
    maintainer_signature_required: bool
    ready_for_review: bool


class MarketplaceError(ValueError):
    """Base class for marketplace domain errors."""


class RejectedManifestError(MarketplaceError):
    """Manifest failed schema, digest, signature, or compatibility checks."""


class DuplicateVersionError(MarketplaceError):
    """The same server version was already published."""


class ServerNotFoundError(MarketplaceError):
    """A server slug or id was not found."""


class UnknownVersionError(MarketplaceError):
    """A requested version is not published for the server."""


class InstallNotFoundError(MarketplaceError):
    """A requested agent install is not present."""


class DuplicateReviewError(MarketplaceError):
    """One workspace can review a server only once."""


class ManifestSignatureVerifier(Protocol):
    def verify(self, manifest: McpServerManifest) -> bool:
        """Return true when the manifest signature is trusted."""


class SigningKey(Protocol):
    def sign(self, payload_digest: str) -> str:
        """Return a detached signature for the payload digest."""


class PublishClient(Protocol):
    def upload_manifest(self, manifest: McpServerManifest) -> str:
        """Upload a signed manifest and return the registry path."""


def compute_manifest_digest(manifest: McpServerManifest) -> str:
    payload = manifest.model_dump(
        mode="json",
        exclude={"manifest_digest", "signature", "manifest_uri"},
    )
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{sha256(body).hexdigest()}"


class TrustedPublisherVerifier:
    """Deterministic verifier mirroring a production cosign/certificate check."""

    def __init__(self, trusted_publishers: Iterable[str]) -> None:
        self._trusted_publishers = frozenset(trusted_publishers)

    def verify(self, manifest: McpServerManifest) -> bool:
        if manifest.publisher not in self._trusted_publishers:
            return False
        return manifest.signature == f"sig:{manifest.signed_by}:{manifest.manifest_digest}"


@dataclass
class InMemoryMarketplaceStore:
    servers: dict[str, MarketplaceServer] = field(default_factory=dict)
    versions: dict[tuple[str, str], McpServerVersion] = field(default_factory=dict)
    installs: dict[tuple[str, str, str], MarketplaceInstall] = field(default_factory=dict)
    reviews: dict[tuple[str, str], MarketplaceReview] = field(default_factory=dict)
    usage: dict[str, MarketplaceUsageAggregate] = field(default_factory=dict)

    def server_by_slug(self, slug: str) -> MarketplaceServer:
        for server in self.servers.values():
            if server.slug == slug:
                return server
        raise ServerNotFoundError(slug)

    def version(self, server_id: str, version: str) -> McpServerVersion:
        key = (server_id, version)
        if key not in self.versions:
            raise UnknownVersionError(f"{server_id}@{version}")
        return self.versions[key]

    def server_versions(self, server_id: str) -> tuple[McpServerVersion, ...]:
        versions = [v for (sid, _version), v in self.versions.items() if sid == server_id]
        return tuple(sorted(versions, key=lambda version: version.published_at_ms))

    def install_count(self, server_id: str) -> int:
        return sum(1 for install in self.installs.values() if install.server_id == server_id)

    def call_count(self, server_id: str) -> int:
        return self.usage.get(
            server_id,
            MarketplaceUsageAggregate(server_id=server_id, installs=0, calls=0),
        ).calls

    def average_rating(self, server_id: str) -> float:
        ratings = [review.rating for review in self.reviews.values() if review.server_id == server_id]
        if not ratings:
            return 0.0
        return round(sum(ratings) / len(ratings), 2)


class QualityScorer:
    def score(
        self,
        *,
        server: MarketplaceServer,
        version: McpServerVersion,
        average_rating: float,
        installs: int,
        calls: int,
    ) -> QualityBreakdown:
        compatibility = min(25, (len(version.tools) * 4) + 9)
        signed_manifest = 25 if version.verified and server.verified else 0
        rating = 15 if average_rating == 0 else round((average_rating / 5.0) * 25)
        usage = min(15, installs + (calls // 10))
        test_health = 10 if version.integration_test_green else 0
        score = min(100, compatibility + signed_manifest + rating + usage + test_health)
        return QualityBreakdown(
            server_id=server.server_id,
            score=score,
            compatibility=compatibility,
            signed_manifest=signed_manifest,
            rating=rating,
            usage=usage,
            test_health=test_health,
        )


class MarketplacePublisher:
    def __init__(
        self,
        *,
        store: InMemoryMarketplaceStore,
        verifier: ManifestSignatureVerifier,
        scorer: QualityScorer | None = None,
    ) -> None:
        self._store = store
        self._verifier = verifier
        self._scorer = scorer or QualityScorer()

    def publish(self, manifest: McpServerManifest, *, now_ms: int) -> PublishResult:
        digest = compute_manifest_digest(manifest)
        if manifest.manifest_digest != digest:
            raise RejectedManifestError("manifest digest mismatch")
        if not self._verifier.verify(manifest):
            raise RejectedManifestError("manifest signature not trusted")

        key = (manifest.server_id, manifest.version)
        if key in self._store.versions:
            raise DuplicateVersionError(f"{manifest.server_id}@{manifest.version}")

        existing = self._store.servers.get(manifest.server_id)
        server = MarketplaceServer(
            server_id=manifest.server_id,
            slug=manifest.slug,
            name=manifest.name,
            publisher=manifest.publisher,
            description=manifest.description,
            categories=manifest.categories,
            created_at_ms=existing.created_at_ms if existing else now_ms,
            verified=True,
            signed_by=manifest.signed_by,
            latest_version=manifest.version,
        )
        provisional_version = McpServerVersion(
            server_id=manifest.server_id,
            version=manifest.version,
            manifest_digest=manifest.manifest_digest,
            image_digest=manifest.image_digest,
            manifest_uri=manifest.manifest_uri,
            signature=manifest.signature,
            tools=manifest.tools,
            scopes=manifest.scopes,
            signed_by=manifest.signed_by,
            published_at_ms=now_ms,
            verified=True,
            active=True,
            integration_test_green=manifest.integration_test_green,
            quality_score=0,
        )
        quality = self._scorer.score(
            server=server,
            version=provisional_version,
            average_rating=self._store.average_rating(manifest.server_id),
            installs=self._store.install_count(manifest.server_id),
            calls=self._store.call_count(manifest.server_id),
        )
        version = provisional_version.model_copy(update={"quality_score": quality.score})
        self._store.servers[manifest.server_id] = server
        self._store.versions[key] = version
        return PublishResult(
            server_id=manifest.server_id,
            version=manifest.version,
            verified=True,
            registry_path=f"registry/mcp/{manifest.slug}/{manifest.version}.json",
            quality_score=quality.score,
        )


class CommunityPublishFlow:
    """PR-based publish gate for community manifests."""

    def __init__(self, *, verifier: ManifestSignatureVerifier) -> None:
        self._verifier = verifier

    def submit(self, manifest: McpServerManifest, *, contributor: str) -> CommunityPublishResult:
        if manifest.manifest_digest != compute_manifest_digest(manifest):
            raise RejectedManifestError("manifest digest mismatch")
        ready = self._verifier.verify(manifest)
        return CommunityPublishResult(
            server_id=manifest.server_id,
            version=manifest.version,
            pull_request_path=f"registry/community/{contributor}/{manifest.slug}.json",
            ci_checks=("schema", "signature", "compatibility", "integration-test"),
            maintainer_signature_required=not ready,
            ready_for_review=ready,
        )


class MarketplaceInstaller:
    def __init__(self, *, store: InMemoryMarketplaceStore) -> None:
        self._store = store

    def install(
        self,
        *,
        workspace_id: str,
        agent_id: str,
        server_id: str,
        version: str,
        installed_by_sub: str,
        now_ms: int,
    ) -> MarketplaceInstall:
        if server_id not in self._store.servers:
            raise ServerNotFoundError(server_id)
        self._store.version(server_id, version)
        key = (workspace_id, agent_id, server_id)
        status: InstallStatus = "installed" if key not in self._store.installs else "upgraded"
        install = MarketplaceInstall(
            workspace_id=workspace_id,
            agent_id=agent_id,
            server_id=server_id,
            version=version,
            installed_by_sub=installed_by_sub,
            installed_at_ms=now_ms,
            status=status,
        )
        self._store.installs[key] = install
        usage = self._store.usage.get(
            server_id,
            MarketplaceUsageAggregate(server_id=server_id, installs=0, calls=0),
        )
        self._store.usage[server_id] = usage.model_copy(update={"installs": usage.installs + 1})
        return install

    def uninstall(self, *, workspace_id: str, agent_id: str, server_id: str) -> MarketplaceInstall:
        key = (workspace_id, agent_id, server_id)
        if key not in self._store.installs:
            raise InstallNotFoundError(server_id)
        removed = self._store.installs.pop(key)
        return removed.model_copy(update={"status": "uninstalled"})

    def installed_for_agent(self, *, workspace_id: str, agent_id: str) -> tuple[InstalledToolView, ...]:
        views: list[InstalledToolView] = []
        for install in self._store.installs.values():
            if install.workspace_id != workspace_id or install.agent_id != agent_id:
                continue
            server = self._store.servers[install.server_id]
            version = self._store.version(install.server_id, install.version)
            views.append(
                InstalledToolView(
                    workspace_id=workspace_id,
                    agent_id=agent_id,
                    server_id=server.server_id,
                    slug=server.slug,
                    name=server.name,
                    pinned_version=install.version,
                    latest_version=server.latest_version,
                    upgrade_available=install.version != server.latest_version,
                    tools=tuple(tool.name for tool in version.tools),
                )
            )
        return tuple(sorted(views, key=lambda view: view.slug))


class MarketplaceBrowser:
    def __init__(self, *, store: InMemoryMarketplaceStore) -> None:
        self._store = store

    def browse(
        self,
        *,
        query: str = "",
        category: str | None = None,
        limit: int = 50,
    ) -> tuple[MarketplaceBrowseItem, ...]:
        normalized = query.strip().lower()
        items: list[MarketplaceBrowseItem] = []
        for server in self._store.servers.values():
            if category and category not in server.categories:
                continue
            version = self._store.version(server.server_id, server.latest_version)
            haystack = " ".join(
                (
                    server.slug,
                    server.name,
                    server.description,
                    " ".join(tool.name for tool in version.tools),
                )
            ).lower()
            if normalized and normalized not in haystack:
                continue
            usage = self._store.usage.get(
                server.server_id,
                MarketplaceUsageAggregate(server_id=server.server_id, installs=0, calls=0),
            )
            items.append(
                MarketplaceBrowseItem(
                    server_id=server.server_id,
                    slug=server.slug,
                    name=server.name,
                    publisher=server.publisher,
                    description=server.description,
                    categories=server.categories,
                    latest_version=server.latest_version,
                    quality_score=version.quality_score,
                    average_rating=self._store.average_rating(server.server_id),
                    installs=usage.installs,
                    calls=usage.calls,
                    install_button_enabled=version.active and version.verified,
                )
            )
        items.sort(key=lambda item: (-item.quality_score, item.slug))
        return tuple(items[:limit])


class MarketplaceReviews:
    _abuse_terms = frozenset({"abuse", "spam", "scam"})

    def __init__(self, *, store: InMemoryMarketplaceStore) -> None:
        self._store = store

    def add_review(
        self,
        *,
        workspace_id: str,
        server_id: str,
        rating: int,
        body: str,
        now_ms: int,
    ) -> MarketplaceReview:
        if server_id not in self._store.servers:
            raise ServerNotFoundError(server_id)
        key = (workspace_id, server_id)
        if key in self._store.reviews:
            raise DuplicateReviewError(server_id)
        normalized = body.lower()
        moderation_required = any(term in normalized for term in self._abuse_terms)
        review = MarketplaceReview(
            workspace_id=workspace_id,
            server_id=server_id,
            rating=rating,
            body=body,
            created_at_ms=now_ms,
            moderation_required=moderation_required,
        )
        self._store.reviews[key] = review
        return review


class MarketplaceAnalytics:
    def __init__(self, *, store: InMemoryMarketplaceStore) -> None:
        self._store = store

    def record_call(
        self,
        *,
        server_id: str,
        opt_in: bool,
        now_ms: int,
    ) -> MarketplaceUsageAggregate:
        if server_id not in self._store.servers:
            raise ServerNotFoundError(server_id)
        current = self._store.usage.get(
            server_id,
            MarketplaceUsageAggregate(server_id=server_id, installs=0, calls=0),
        )
        if not opt_in:
            return current
        updated = current.model_copy(
            update={"calls": current.calls + 1, "last_called_at_ms": now_ms}
        )
        self._store.usage[server_id] = updated
        return updated


class MarketplaceAcceptanceGate:
    def __init__(self, *, store: InMemoryMarketplaceStore, min_servers: int = 25) -> None:
        self._store = store
        self._min_servers = min_servers

    def assert_ready(self) -> tuple[MarketplaceBrowseItem, ...]:
        items = MarketplaceBrowser(store=self._store).browse(limit=1000)
        if len(items) < self._min_servers:
            raise RejectedManifestError(f"expected at least {self._min_servers} active servers")
        weak = [item.slug for item in items if item.quality_score <= 0 or not item.install_button_enabled]
        if weak:
            raise RejectedManifestError(f"servers not marketplace-ready: {', '.join(weak)}")
        return items


class ServerPublishCli:
    """Pure seam for `loop tool publish`: sign, upload, and return registry path."""

    def __init__(self, *, signer: SigningKey, client: PublishClient) -> None:
        self._signer = signer
        self._client = client

    def publish(self, manifest: McpServerManifest) -> PublishResult:
        digest = compute_manifest_digest(manifest)
        signed = manifest.model_copy(
            update={
                "manifest_digest": digest,
                "signature": self._signer.sign(digest),
            }
        )
        registry_path = self._client.upload_manifest(signed)
        return PublishResult(
            server_id=signed.server_id,
            version=signed.version,
            verified=True,
            registry_path=registry_path,
            quality_score=0,
        )


class FirstPartyCatalog:
    def manifests(self) -> tuple[McpServerManifest, ...]:
        return first_party_manifests()

    def publish_all(self, publisher: MarketplacePublisher, *, now_ms: int) -> tuple[PublishResult, ...]:
        results: list[PublishResult] = []
        for offset, manifest in enumerate(self.manifests()):
            results.append(publisher.publish(manifest, now_ms=now_ms + offset))
        return tuple(results)


def first_party_manifests() -> tuple[McpServerManifest, ...]:
    specs = (
        _spec(
            "salesforce",
            "Salesforce",
            "Read Salesforce objects, records, and account detail.",
            ("crm", "read"),
            "oauth2",
            ("api", "refresh_token"),
            (
                _tool("list_objects", "List CRM object types.", "read"),
                _tool("query_records", "Run SOQL-style record queries.", "read"),
                _tool("get_record_detail", "Fetch a single CRM record.", "read"),
            ),
        ),
        _spec(
            "zendesk",
            "Zendesk",
            "Read tickets and add scoped support comments.",
            ("support", "crm"),
            "oauth2",
            ("tickets:read", "tickets:write"),
            (
                _tool("list_tickets", "List support tickets.", "read"),
                _tool("get_ticket", "Read ticket detail.", "read"),
                _tool("add_comment", "Add an internal ticket comment.", "write"),
            ),
        ),
        _spec(
            "hubspot-read",
            "HubSpot Read",
            "Read contacts, companies, and deal pipelines.",
            ("crm", "read"),
            "oauth2",
            ("crm.objects.contacts.read", "crm.objects.deals.read"),
            (
                _tool("list_contacts", "List HubSpot contacts.", "read"),
                _tool("list_companies", "List HubSpot companies.", "read"),
                _tool("list_deals", "List HubSpot deals.", "read"),
            ),
        ),
        _spec(
            "stripe-read",
            "Stripe Read",
            "Read customers, invoices, payouts, and balances in test mode.",
            ("billing", "read"),
            "api_key",
            ("read_only",),
            (
                _tool("list_customers", "List Stripe customers.", "read"),
                _tool("list_invoices", "List Stripe invoices.", "read"),
                _tool("list_payouts", "List Stripe payouts.", "read"),
            ),
        ),
        _spec(
            "google-calendar",
            "Google Calendar",
            "Read and create calendar events through OAuth2.",
            ("productivity", "calendar"),
            "oauth2",
            ("https://www.googleapis.com/auth/calendar.events",),
            (
                _tool("list_events", "List upcoming calendar events.", "read"),
                _tool("create_event", "Create a calendar event.", "write"),
            ),
        ),
        _spec(
            "gmail",
            "Gmail",
            "Read mail, create drafts, and send messages from Gmail.",
            ("productivity", "email"),
            "oauth2",
            ("https://www.googleapis.com/auth/gmail.send",),
            (
                _tool("search_messages", "Search Gmail messages.", "read"),
                _tool("create_draft", "Create a Gmail draft.", "write"),
                _tool("send_message", "Send a Gmail message.", "write"),
            ),
        ),
        _spec(
            "github",
            "GitHub",
            "Create issues, comment, and list pull requests.",
            ("engineering", "source"),
            "app",
            ("issues:write", "pull_requests:read"),
            (
                _tool("create_issue", "Create a GitHub issue.", "write"),
                _tool("comment_on_issue", "Comment on a GitHub issue.", "write"),
                _tool("list_pull_requests", "List repository pull requests.", "read"),
            ),
        ),
        _spec(
            "linear",
            "Linear",
            "Manage Linear issues and projects.",
            ("engineering", "project"),
            "api_key",
            ("issues:read", "issues:write", "projects:read"),
            (
                _tool("list_issues", "List Linear issues.", "read"),
                _tool("create_issue", "Create a Linear issue.", "write"),
                _tool("update_issue", "Update a Linear issue.", "write"),
                _tool("list_projects", "List Linear projects.", "read"),
            ),
        ),
        _spec(
            "jira",
            "Jira",
            "Create, update, and comment on Jira issues.",
            ("engineering", "project"),
            "api_key",
            ("read:jira-work", "write:jira-work"),
            (
                _tool("list_issues", "List Jira issues.", "read"),
                _tool("create_issue", "Create a Jira issue.", "write"),
                _tool("add_comment", "Add a Jira comment.", "write"),
            ),
        ),
        _spec(
            "notion",
            "Notion",
            "Query databases and create pages.",
            ("knowledge", "docs"),
            "oauth2",
            ("databases:read", "pages:write"),
            (
                _tool("query_database", "Query a Notion database.", "read"),
                _tool("create_page", "Create a Notion page.", "write"),
            ),
        ),
        _spec(
            "asana",
            "Asana",
            "Read projects and manage Asana tasks.",
            ("project", "productivity"),
            "pat",
            ("default",),
            (
                _tool("list_projects", "List Asana projects.", "read"),
                _tool("create_task", "Create an Asana task.", "write"),
                _tool("update_task", "Update an Asana task.", "write"),
            ),
        ),
        _spec(
            "stripe-write",
            "Stripe Write",
            "Create invoices and refunds with test-mode safeguards.",
            ("billing", "write"),
            "api_key",
            ("refunds:write", "invoices:write"),
            (
                _tool("create_refund", "Create a test-mode refund.", "write"),
                _tool("create_invoice", "Create a test-mode invoice.", "write"),
            ),
        ),
        _spec(
            "slack-write",
            "Slack Write",
            "Post channel messages and direct messages.",
            ("communication", "write"),
            "oauth2",
            ("chat:write", "im:write"),
            (
                _tool("post_message", "Post a Slack channel message.", "write"),
                _tool("send_direct_message", "Send a Slack DM.", "write"),
            ),
        ),
        _spec(
            "hubspot-write",
            "HubSpot Write",
            "Create contacts and update deals in HubSpot.",
            ("crm", "write"),
            "oauth2",
            ("crm.objects.contacts.write", "crm.objects.deals.write"),
            (
                _tool("create_contact", "Create a HubSpot contact.", "write"),
                _tool("update_deal", "Update a HubSpot deal.", "write"),
            ),
        ),
        _spec(
            "web-search",
            "Web Search",
            "Search the web with Tavily and Brave while tracking latency and cost.",
            ("research", "search"),
            "api_key",
            ("tavily", "brave"),
            (
                _tool("tavily_search", "Search via Tavily with cost metadata.", "read"),
                _tool("brave_search", "Search via Brave with latency metadata.", "read"),
            ),
        ),
    )
    additional = (
        ("google-drive", "Google Drive", "Search and manage Drive files.", ("docs", "storage")),
        ("outlook-email", "Outlook Email", "Read and send Outlook email.", ("email", "productivity")),
        ("outlook-calendar", "Outlook Calendar", "Manage Outlook calendar.", ("calendar",)),
        ("sharepoint", "SharePoint", "Search SharePoint documents.", ("docs", "enterprise")),
        ("teams", "Teams", "Post Teams messages.", ("communication",)),
        ("discord", "Discord", "Read and send Discord messages.", ("communication",)),
        ("twilio-sms", "Twilio SMS", "Send SMS through Twilio.", ("communication", "sms")),
        ("whatsapp", "WhatsApp", "Send WhatsApp templates.", ("communication",)),
        ("rcs", "RCS", "Send RCS business messages.", ("communication",)),
        ("postgres", "Postgres", "Run approved database queries.", ("database",)),
        ("clickhouse", "ClickHouse", "Run approved analytics queries.", ("database",)),
    )
    filler = tuple(
        _spec(
            slug,
            name,
            description,
            categories,
            "oauth2" if "outlook" in slug or slug in {"google-drive", "sharepoint"} else "api_key",
            ("default",),
            (
                _tool("read", f"Read from {name}.", "read"),
                _tool("write", f"Write to {name} with scoped permissions.", "write"),
            ),
        )
        for slug, name, description, categories in additional
    )
    return specs + filler


def _tool(name: str, description: str, risk: RiskKind) -> McpToolSpec:
    return McpToolSpec(name=name, description=description, risk=risk)


def _spec(
    slug: str,
    name: str,
    description: str,
    categories: Sequence[str],
    auth_type: AuthKind,
    scopes: Sequence[str],
    tools: Sequence[McpToolSpec],
) -> McpServerManifest:
    base = McpServerManifest(
        server_id=f"first-party.{slug}",
        slug=slug,
        name=name,
        publisher="loop",
        description=description,
        version="1.0.0",
        categories=tuple(categories),
        capabilities=("mcp", "tool-call", "sandbox-tested"),
        tools=tuple(tools),
        auth_type=auth_type,
        scopes=tuple(scopes),
        source_url=f"https://github.com/loop/servers/{slug}",
        image_digest=f"sha256:{sha256(slug.encode()).hexdigest()}",
        manifest_digest="sha256:pending",
        manifest_uri=f"registry/mcp/{slug}/1.0.0.json",
        signature="sig:pending",
        signed_by="loop-maintainer",
    )
    digest = compute_manifest_digest(base)
    return base.model_copy(
        update={
            "manifest_digest": digest,
            "signature": f"sig:loop-maintainer:{digest}",
        }
    )

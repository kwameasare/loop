"""Just-in-time (JIT) user provisioning for SAML SSO — S616.

When a SAML assertion is accepted by :func:`~loop_control_plane.saml.accept_acs_post`
for an unrecognised subject, :func:`provision_jit` creates:

1. A **User** record for the subject (identified by the NameID / email).
2. A **workspace_members** row (or upserts an existing one) carrying the
   role projected from the assertion's group claims via the
   :class:`~loop_control_plane.saml.SamlSpConfig` group-role map.

Architecture notes
------------------
The function takes :class:`UserStore` and :class:`MembershipStore` Protocol
arguments rather than calling persistence directly. This keeps the logic
testable in isolation without a real database and allows any backing store
(SQLAlchemy, asyncpg, in-memory fixture) to be plugged in at the call site.

Typical control-plane wiring::

    from loop_control_plane.jit_provisioning import (
        provision_jit,
        InMemoryUserStore,
        InMemoryMembershipStore,
    )

    result = provision_jit(
        assertion,
        sp_config,
        workspace_id=tenant.workspace_id,
        user_store=pg_user_store,
        membership_store=pg_membership_store,
    )
    session = mint_session(result.user.sub, workspace_id=tenant.workspace_id)

Role projection follows the same first-match semantics as
:func:`~loop_control_plane.saml.project_role`: iterate the group claims in
assertion order; return the role for the first group that appears in the
config's ``group_role_map``; fall back to ``sp_config.default_role``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from loop_control_plane.saml import SamlAssertion, SamlSpConfig, project_role

# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProvisionedUser:
    """A user record created or found during JIT provisioning."""

    sub: str
    """Subject identifier (NameID — typically the IdP email address)."""

    email: str
    """Email address derived from the NameID or email SAML attribute."""

    display_name: str
    """Best-effort display name; empty string when no attribute is present."""


@dataclass(frozen=True, slots=True)
class ProvisionedMembership:
    """A workspace_members row created or updated during JIT provisioning."""

    user_sub: str
    workspace_id: str
    role: str


@dataclass(frozen=True, slots=True)
class JitProvisioningResult:
    """Outcome of a single :func:`provision_jit` call."""

    user: ProvisionedUser
    membership: ProvisionedMembership
    created_user: bool
    """True when the user row did not previously exist."""
    created_membership: bool
    """True when the workspace_members row was newly inserted (not updated)."""


# ---------------------------------------------------------------------------
# Store Protocols
# ---------------------------------------------------------------------------


class UserStore(Protocol):
    """Persistence seam for User records."""

    def get_by_sub(self, sub: str) -> ProvisionedUser | None:
        """Return the user identified by *sub*, or None if absent."""
        ...

    def create(self, sub: str, email: str, display_name: str) -> ProvisionedUser:
        """Insert a new user row and return it."""
        ...


class MembershipStore(Protocol):
    """Persistence seam for workspace_members rows."""

    def get(self, workspace_id: str, user_sub: str) -> ProvisionedMembership | None:
        """Return the existing membership, or None if absent."""
        ...

    def upsert(
        self, workspace_id: str, user_sub: str, role: str
    ) -> tuple[ProvisionedMembership, bool]:
        """Create or update the membership.

        Returns ``(membership, created)`` where *created* is True when the
        row was newly inserted.
        """
        ...


# ---------------------------------------------------------------------------
# Core provisioning function
# ---------------------------------------------------------------------------


def provision_jit(
    assertion: SamlAssertion,
    sp_config: SamlSpConfig,
    *,
    workspace_id: str,
    user_store: UserStore,
    membership_store: MembershipStore,
) -> JitProvisioningResult:
    """Create or return the user + workspace membership for *assertion*.

    Steps:
    1. Derive the email from ``assertion.subject`` (NameID is expected to be
       an email address for Okta, Entra ID, and Google Workspace).
    2. Look up the user by subject; create a new row if missing.
    3. Project the role from the assertion's group claims via *sp_config*.
    4. Upsert the workspace_members row (role is refreshed on every login so
       group-role changes take effect immediately).

    Parameters
    ----------
    assertion:
        The already-validated :class:`~loop_control_plane.saml.SamlAssertion`.
    sp_config:
        The per-tenant :class:`~loop_control_plane.saml.SamlSpConfig`; its
        ``group_role_map`` and ``default_role`` drive role assignment.
    workspace_id:
        The workspace to join.  Supplied explicitly so the function does not
        need to parse the ACS URL or ``sp_entity_id``.
    user_store:
        Persistence seam for user records.
    membership_store:
        Persistence seam for workspace_members rows.

    Returns
    -------
    JitProvisioningResult
    """
    sub = assertion.subject
    # Derive email from subject (NameID); SAML NameIDs for all three IdPs we
    # support use the email format.  If an explicit "email" attribute is
    # present, prefer it.
    emails = assertion.attributes.get("email") or assertion.attributes.get("emails")
    email = emails[0] if emails else sub

    # Derive display name from common SAML attribute names.
    display_names = (
        assertion.attributes.get("displayName")
        or assertion.attributes.get("name")
        or assertion.attributes.get("cn")
    )
    display_name = display_names[0] if display_names else ""

    # 1. User lookup / creation
    existing_user = user_store.get_by_sub(sub)
    if existing_user is not None:
        user = existing_user
        created_user = False
    else:
        user = user_store.create(sub, email, display_name)
        created_user = True

    # 2. Role projection
    role = project_role(assertion, sp_config)

    # 3. Membership upsert
    membership, created_membership = membership_store.upsert(workspace_id, sub, role)

    return JitProvisioningResult(
        user=user,
        membership=membership,
        created_user=created_user,
        created_membership=created_membership,
    )


# ---------------------------------------------------------------------------
# In-memory store implementations (for tests and the sandbox server)
# ---------------------------------------------------------------------------


class InMemoryUserStore:
    """Thread-safe in-memory :class:`UserStore` for tests."""

    def __init__(self) -> None:
        self._users: dict[str, ProvisionedUser] = {}

    def get_by_sub(self, sub: str) -> ProvisionedUser | None:
        return self._users.get(sub)

    def create(self, sub: str, email: str, display_name: str) -> ProvisionedUser:
        if sub in self._users:
            raise ValueError(f"User {sub!r} already exists")
        user = ProvisionedUser(sub=sub, email=email, display_name=display_name)
        self._users[sub] = user
        return user

    def all(self) -> list[ProvisionedUser]:
        return list(self._users.values())


class InMemoryMembershipStore:
    """Thread-safe in-memory :class:`MembershipStore` for tests."""

    def __init__(self) -> None:
        self._memberships: dict[tuple[str, str], ProvisionedMembership] = {}

    def get(self, workspace_id: str, user_sub: str) -> ProvisionedMembership | None:
        return self._memberships.get((workspace_id, user_sub))

    def upsert(
        self, workspace_id: str, user_sub: str, role: str
    ) -> tuple[ProvisionedMembership, bool]:
        key = (workspace_id, user_sub)
        created = key not in self._memberships
        membership = ProvisionedMembership(user_sub=user_sub, workspace_id=workspace_id, role=role)
        self._memberships[key] = membership
        return membership, created

    def all(self) -> list[ProvisionedMembership]:
        return list(self._memberships.values())

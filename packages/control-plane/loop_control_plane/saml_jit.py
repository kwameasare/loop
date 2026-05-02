"""Just-in-Time (JIT) user provisioning for SAML SSO — S616.

When a SAML assertion is accepted at the ACS endpoint
(:func:`loop_control_plane.saml.accept_acs_post`) and the assertion
subject does not yet exist in the ``users`` table, the control-plane
provisions the user and the workspace_members row in one atomic
operation before minting a session. This module is the seam.

Design notes
------------

* The persistence layer is hidden behind :class:`UserStore` (Protocol)
  so this code can be unit-tested without Postgres. The cp-api wires
  a SQLAlchemy-backed store; tests use :class:`InMemoryUserStore`.
* Identity is keyed on ``(auth_provider, auth_subject)``. The
  ``users.UNIQUE(auth_provider, auth_subject)`` constraint
  (cp_0001 migration) makes this lookup canonical. Email is **not**
  the primary identity key — IdPs can rename email addresses.
* Email collision handling: if a user already exists with the same
  email but a *different* (provider, subject) pair we refuse to
  silently re-bind the row (that would let a misconfigured IdP take
  over an existing account). Returns a :class:`JitCollisionError`
  instead.
* Idempotent: a repeat login for an existing (provider, subject) pair
  re-uses the user row and only upserts the workspace_members role
  (no duplicate user, no duplicate member). The role can change
  between logins (e.g. the IdP moves the user from Editors to
  Admins) — we update the existing membership row to match.

The function returns a :class:`JitProvisionResult` with both the
user/member rows *and* boolean flags so the cp-api can emit
``user.created`` / ``workspace.member.added`` audit events.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from loop_control_plane.saml import AcsResult


class JitProvisionError(ValueError):
    """Base class for JIT provisioning failures."""


class JitCollisionError(JitProvisionError):
    """An existing user has the same email but a different IdP subject.

    We refuse to silently rebind the existing user row to a new
    ``(auth_provider, auth_subject)`` pair: that would let a
    misconfigured IdP take over an existing account. Operator must
    manually merge or delete the conflicting row.
    """


@dataclass(frozen=True, slots=True)
class JitUser:
    id: uuid.UUID
    email: str
    full_name: str | None
    auth_provider: str
    auth_subject: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class JitMember:
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class JitProvisionResult:
    user: JitUser
    member: JitMember
    created_user: bool
    """True iff the user row was inserted by this call."""
    created_member: bool
    """True iff the workspace_members row was inserted by this call."""
    role_changed: bool
    """True iff a pre-existing membership had its role updated."""


class UserStore(Protocol):
    """Persistence seam for JIT provisioning.

    Implementations MUST be transactional across the full
    :func:`jit_provision` call — the cp-api wrapper opens a single
    SQLAlchemy session/transaction and passes a store bound to it.
    """

    def find_user_by_subject(
        self, *, auth_provider: str, auth_subject: str
    ) -> JitUser | None: ...

    def find_user_by_email(self, email: str) -> JitUser | None: ...

    def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        auth_provider: str,
        auth_subject: str,
        now: datetime,
    ) -> JitUser: ...

    def get_member(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> JitMember | None: ...

    def create_member(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        now: datetime,
    ) -> JitMember: ...

    def update_member_role(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> JitMember: ...


class InMemoryUserStore:
    """Reference :class:`UserStore` for unit tests + sandbox tenants."""

    def __init__(self) -> None:
        self._users_by_id: dict[uuid.UUID, JitUser] = {}
        self._users_by_subject: dict[tuple[str, str], JitUser] = {}
        self._users_by_email: dict[str, JitUser] = {}
        self._members: dict[tuple[uuid.UUID, uuid.UUID], JitMember] = {}

    def find_user_by_subject(
        self, *, auth_provider: str, auth_subject: str
    ) -> JitUser | None:
        return self._users_by_subject.get((auth_provider, auth_subject))

    def find_user_by_email(self, email: str) -> JitUser | None:
        return self._users_by_email.get(email.lower())

    def create_user(
        self,
        *,
        email: str,
        full_name: str | None,
        auth_provider: str,
        auth_subject: str,
        now: datetime,
    ) -> JitUser:
        user = JitUser(
            id=uuid.uuid4(),
            email=email,
            full_name=full_name,
            auth_provider=auth_provider,
            auth_subject=auth_subject,
            created_at=now,
        )
        self._users_by_id[user.id] = user
        self._users_by_subject[(auth_provider, auth_subject)] = user
        self._users_by_email[email.lower()] = user
        return user

    def get_member(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> JitMember | None:
        return self._members.get((workspace_id, user_id))

    def create_member(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        now: datetime,
    ) -> JitMember:
        member = JitMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            created_at=now,
        )
        self._members[(workspace_id, user_id)] = member
        return member

    def update_member_role(
        self, *, workspace_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> JitMember:
        existing = self._members[(workspace_id, user_id)]
        updated = JitMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
            created_at=existing.created_at,
        )
        self._members[(workspace_id, user_id)] = updated
        return updated


_VALID_ROLES = frozenset({"owner", "admin", "editor", "operator", "viewer"})


def _extract_email_and_name(acs: AcsResult) -> tuple[str, str | None]:
    """Pull the email and (optional) display name from the assertion.

    SAML attribute names vary by IdP. We accept the canonical
    NameID-as-email *or* the standard ``email`` attribute, plus a
    handful of well-known display-name attributes. Strict validation
    of the email format is performed at the ACS layer; here we only
    pick a value.
    """
    attrs = acs.assertion.attributes
    email_candidates = (
        attrs.get("email", []),
        attrs.get("emailaddress", []),
        attrs.get(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            [],
        ),
    )
    email = ""
    for candidates in email_candidates:
        if candidates:
            email = candidates[0]
            break
    if not email:
        # Fall back to the NameID — Okta/Google/Entra all emit
        # email-format NameIDs by default for email-mapped subjects.
        email = acs.assertion.subject

    name_candidates = (
        attrs.get("displayName", []),
        attrs.get("name", []),
        attrs.get(
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
            [],
        ),
    )
    full_name: str | None = None
    for candidates in name_candidates:
        if candidates:
            full_name = candidates[0]
            break

    return email, full_name


def jit_provision(
    acs: AcsResult,
    *,
    workspace_id: uuid.UUID,
    auth_provider: str,
    store: UserStore,
    now: datetime | None = None,
) -> JitProvisionResult:
    """Provision (or refresh) the user + workspace_members row for an SSO login.

    Args:
        acs: The validated ACS result (subject, role, assertion).
        workspace_id: Target workspace.
        auth_provider: ``"saml-okta"`` / ``"saml-entra"`` /
            ``"saml-google"`` — the cp-api decides this based on the
            tenant_sso config row.
        store: Persistence seam (see :class:`UserStore`).
        now: Optional injected clock for tests.

    Raises:
        JitCollisionError: Existing user with same email but different
            ``(auth_provider, auth_subject)`` pair.
        JitProvisionError: Invalid role projection.
    """
    if acs.role not in _VALID_ROLES:
        raise JitProvisionError(
            f"projected role {acs.role!r} is not a valid workspace role"
        )

    instant = now if now is not None else datetime.now(UTC)
    auth_subject = acs.assertion.subject
    email, full_name = _extract_email_and_name(acs)

    existing = store.find_user_by_subject(
        auth_provider=auth_provider, auth_subject=auth_subject
    )
    created_user = False
    if existing is None:
        # No row for this IdP subject. Check email-collision before
        # we create.
        email_collision = store.find_user_by_email(email)
        if email_collision is not None and (
            email_collision.auth_provider != auth_provider
            or email_collision.auth_subject != auth_subject
        ):
            raise JitCollisionError(
                f"user with email {email!r} already exists under a different "
                f"identity ({email_collision.auth_provider}/"
                f"{email_collision.auth_subject!r}); operator must reconcile"
            )
        user = store.create_user(
            email=email,
            full_name=full_name,
            auth_provider=auth_provider,
            auth_subject=auth_subject,
            now=instant,
        )
        created_user = True
    else:
        user = existing

    member = store.get_member(workspace_id=workspace_id, user_id=user.id)
    created_member = False
    role_changed = False
    if member is None:
        member = store.create_member(
            workspace_id=workspace_id,
            user_id=user.id,
            role=acs.role,
            now=instant,
        )
        created_member = True
    elif member.role != acs.role:
        member = store.update_member_role(
            workspace_id=workspace_id, user_id=user.id, role=acs.role
        )
        role_changed = True

    return JitProvisionResult(
        user=user,
        member=member,
        created_user=created_user,
        created_member=created_member,
        role_changed=role_changed,
    )

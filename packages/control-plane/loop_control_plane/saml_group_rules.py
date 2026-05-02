"""Workspace SAML group → role mapping rules — S617.

Backs the ``workspace_sso_group_rules`` table introduced by
``cp_0005_sso_group_rules``. Operators edit the mapping in the
Studio enterprise SSO tab; the cp-api persists rows here and the
SAML ACS handler loads them via :func:`load_group_rules` to build
the :class:`~loop_control_plane.saml.SamlSpConfig` group_role_map.

Design seam:
    The persistence layer is a :class:`GroupRuleStore` Protocol so
    we can unit-test the validation + projection logic without a
    Postgres round-trip. The cp-api wires a SQLAlchemy-backed store;
    sandbox tenants and tests use :class:`InMemoryGroupRuleStore`.

Validation invariants (enforced by :func:`upsert_group_rule`):
    * role must be one of ``owner | admin | editor | operator | viewer``.
    * group_name must be non-empty and ≤ 256 chars (matches Okta /
      Entra / Workspace group-name limits).
    * (workspace_id, group_name) is unique — re-upserting with a
      different role replaces the existing rule.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from loop_control_plane.saml import GroupRoleMapping


VALID_ROLES: frozenset[str] = frozenset(
    {"owner", "admin", "editor", "operator", "viewer"}
)
MAX_GROUP_NAME_LEN = 256


class GroupRuleError(ValueError):
    """Validation failure on a SAML group-rule write."""


@dataclass(frozen=True, slots=True)
class GroupRule:
    id: uuid.UUID
    workspace_id: uuid.UUID
    group_name: str
    role: str
    created_at: datetime
    created_by: uuid.UUID | None


class GroupRuleStore(Protocol):
    def list_rules(self, workspace_id: uuid.UUID) -> tuple[GroupRule, ...]: ...
    def upsert(
        self,
        *,
        workspace_id: uuid.UUID,
        group_name: str,
        role: str,
        created_by: uuid.UUID | None,
        now: datetime,
    ) -> GroupRule: ...
    def delete(
        self, *, workspace_id: uuid.UUID, group_name: str
    ) -> bool: ...


class InMemoryGroupRuleStore:
    """Reference :class:`GroupRuleStore` for tests + sandbox tenants."""

    def __init__(self) -> None:
        self._rows: dict[tuple[uuid.UUID, str], GroupRule] = {}

    def list_rules(self, workspace_id: uuid.UUID) -> tuple[GroupRule, ...]:
        return tuple(
            sorted(
                (rule for (ws, _), rule in self._rows.items() if ws == workspace_id),
                key=lambda r: r.group_name,
            )
        )

    def upsert(
        self,
        *,
        workspace_id: uuid.UUID,
        group_name: str,
        role: str,
        created_by: uuid.UUID | None,
        now: datetime,
    ) -> GroupRule:
        key = (workspace_id, group_name)
        existing = self._rows.get(key)
        rule = GroupRule(
            id=existing.id if existing else uuid.uuid4(),
            workspace_id=workspace_id,
            group_name=group_name,
            role=role,
            created_at=existing.created_at if existing else now,
            created_by=existing.created_by if existing else created_by,
        )
        self._rows[key] = rule
        return rule

    def delete(self, *, workspace_id: uuid.UUID, group_name: str) -> bool:
        return self._rows.pop((workspace_id, group_name), None) is not None


def _validate(group_name: str, role: str) -> None:
    if not group_name or not group_name.strip():
        raise GroupRuleError("group_name must be non-empty")
    if len(group_name) > MAX_GROUP_NAME_LEN:
        raise GroupRuleError(
            f"group_name exceeds {MAX_GROUP_NAME_LEN} character limit"
        )
    if role not in VALID_ROLES:
        raise GroupRuleError(
            f"role {role!r} is not one of {sorted(VALID_ROLES)}"
        )


def upsert_group_rule(
    *,
    workspace_id: uuid.UUID,
    group_name: str,
    role: str,
    store: GroupRuleStore,
    created_by: uuid.UUID | None = None,
    now: datetime | None = None,
) -> GroupRule:
    """Validate inputs, then upsert the rule via the store.

    Re-upserting (workspace_id, group_name) with a different role
    replaces the role; the row id and created_at are preserved so
    audit history stays attached to the original creation.
    """
    _validate(group_name, role)
    instant = now if now is not None else datetime.now(UTC)
    return store.upsert(
        workspace_id=workspace_id,
        group_name=group_name,
        role=role,
        created_by=created_by,
        now=instant,
    )


def delete_group_rule(
    *, workspace_id: uuid.UUID, group_name: str, store: GroupRuleStore
) -> bool:
    """Delete a rule. Returns True iff a row was removed."""
    return store.delete(workspace_id=workspace_id, group_name=group_name)


def load_group_rules(
    workspace_id: uuid.UUID, *, store: GroupRuleStore
) -> tuple[GroupRoleMapping, ...]:
    """Materialise the stored rules into the immutable tuple shape
    consumed by :class:`~loop_control_plane.saml.SamlSpConfig`."""
    return tuple(
        GroupRoleMapping(group=rule.group_name, role=rule.role)
        for rule in store.list_rules(workspace_id)
    )

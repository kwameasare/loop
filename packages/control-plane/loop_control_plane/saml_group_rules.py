"""SAML group → workspace role mapping rules — S617.

Provides persistent storage of the per-workspace group-to-role rules table
(``workspace_sso_groups``) plus an in-memory implementation for tests and
sandbox deployments.

Usage
-----
::

    store = InMemoryGroupRuleStore()
    store.set_rules("ws-abc", [
        GroupRuleRecord("ws-abc", "admins", "admin"),
        GroupRuleRecord("ws-abc", "team",   "editor"),
    ])

    # Build SamlSpConfig from stored rules
    from loop_control_plane.saml import SamlSpConfig
    rules = store.list_rules("ws-abc")
    sp = SamlSpConfig(
        ...,
        group_role_map=rules_to_group_role_map(rules),
        default_role="viewer",
    )

Schema note
-----------
The logical ``workspace_sso_groups`` table has columns:
``workspace_id TEXT, group TEXT, role TEXT, PRIMARY KEY (workspace_id, group)``

All roles must be one of the canonical Loop roles:
``owner | admin | editor | operator | viewer``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from loop_control_plane.saml import GroupRoleMapping

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_ROLES: frozenset[str] = frozenset({"owner", "admin", "editor", "operator", "viewer"})


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroupRuleRecord:
    """A single row in the ``workspace_sso_groups`` table.

    Attributes
    ----------
    workspace_id:
        The workspace this rule belongs to.
    group:
        IdP group name exactly as it appears in the SAML ``groups`` attribute.
    role:
        Loop workspace role to grant.  Must be one of ``VALID_ROLES``.
    """

    workspace_id: str
    group: str
    role: str

    def __post_init__(self) -> None:
        if not self.workspace_id:
            raise ValueError("workspace_id must not be empty")
        if not self.group:
            raise ValueError("group must not be empty")
        if self.role not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)!r}, got {self.role!r}")


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class GroupRuleStore(Protocol):
    """Persistence interface for group→role mapping rules."""

    def list_rules(self, workspace_id: str) -> list[GroupRuleRecord]:
        """Return all rules for *workspace_id* ordered by group name."""
        ...

    def set_rules(self, workspace_id: str, rules: list[GroupRuleRecord]) -> None:
        """Replace all rules for *workspace_id* with *rules*.

        Parameters
        ----------
        workspace_id:
            Target workspace.
        rules:
            New rule set.  Every record must have
            ``record.workspace_id == workspace_id``.  Duplicate groups are
            rejected.

        Raises
        ------
        ValueError
            If any record belongs to a different workspace or if the same
            group appears more than once.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation (tests / sandbox)
# ---------------------------------------------------------------------------


class InMemoryGroupRuleStore:
    """Thread-unsafe in-memory implementation of :class:`GroupRuleStore`."""

    def __init__(self) -> None:
        # workspace_id → ordered list of GroupRuleRecord
        self._data: dict[str, list[GroupRuleRecord]] = {}

    # GroupRuleStore protocol

    def list_rules(self, workspace_id: str) -> list[GroupRuleRecord]:
        return list(self._data.get(workspace_id, []))

    def set_rules(self, workspace_id: str, rules: list[GroupRuleRecord]) -> None:
        seen_groups: set[str] = set()
        for record in rules:
            if record.workspace_id != workspace_id:
                raise ValueError(
                    f"Record workspace_id {record.workspace_id!r} does not "
                    f"match target {workspace_id!r}"
                )
            if record.group in seen_groups:
                raise ValueError(f"Duplicate group {record.group!r} in rule set")
            seen_groups.add(record.group)
        self._data[workspace_id] = sorted(rules, key=lambda r: r.group)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def rules_to_group_role_map(
    rules: list[GroupRuleRecord],
) -> tuple[GroupRoleMapping, ...]:
    """Convert a list of :class:`GroupRuleRecord` to a ``group_role_map``
    tuple suitable for :class:`~loop_control_plane.saml.SamlSpConfig`.

    Priority is determined by ``project_role``'s built-in privilege order,
    not by rule insertion order.
    """
    return tuple(GroupRoleMapping(group=r.group, role=r.role) for r in rules)

"""In-memory :class:`ScimStore` implementation for tests + sandbox tenants.

Production cp-api wires a Postgres-backed store; this in-memory one
keeps the REST contract honest in CI without DB infra. Per-tenant
isolation is enforced by partitioning the dict by tenant id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from loop_control_plane.scim import (
    ScimError,
    ScimFilter,
    ScimGroup,
    ScimMeta,
    ScimUser,
    _etag,
    new_group_id,
    new_user_id,
)


@dataclass(slots=True)
class _Tenant:
    users: dict[str, ScimUser] = field(default_factory=dict)
    groups: dict[str, ScimGroup] = field(default_factory=dict)


class InMemoryScimStore:
    """Thread-unsafe in-memory store; suitable for tests + the
    sandbox-tenant flow only."""

    def __init__(self) -> None:
        self._tenants: dict[str, _Tenant] = {}

    def _t(self, tenant_id: str) -> _Tenant:
        return self._tenants.setdefault(tenant_id, _Tenant())

    # ── Users ──
    def list_users(
        self, tenant_id: str, filt: ScimFilter | None, start_index: int, count: int
    ) -> tuple[list[ScimUser], int]:
        users = list(self._t(tenant_id).users.values())
        if filt is not None:
            users = [u for u in users if _match_user(u, filt)]
        users.sort(key=lambda u: u.id)
        total = len(users)
        page = users[max(start_index - 1, 0) : max(start_index - 1, 0) + max(count, 0)]
        return page, total

    def get_user(self, tenant_id: str, user_id: str) -> ScimUser | None:
        return self._t(tenant_id).users.get(user_id)

    def create_user(self, tenant_id: str, user: ScimUser, now: datetime) -> ScimUser:
        users = self._t(tenant_id).users
        for existing in users.values():
            if existing.user_name == user.user_name:
                raise ScimError(409, f"userName {user.user_name!r} already exists", "uniqueness")
        if not user.id:
            user.id = new_user_id()
        user.meta = ScimMeta(
            resource_type="User",
            created=now,
            last_modified=now,
            version=_etag(now),
        )
        users[user.id] = user
        return user

    def replace_user(self, tenant_id: str, user_id: str, user: ScimUser, now: datetime) -> ScimUser:
        users = self._t(tenant_id).users
        if user_id not in users:
            raise ScimError(404, f"user {user_id} not found")
        # Preserve created timestamp; bump lastModified.
        original = users[user_id]
        for existing in users.values():
            if existing.id != user_id and existing.user_name == user.user_name:
                raise ScimError(409, f"userName {user.user_name!r} already exists", "uniqueness")
        user.id = user_id
        user.meta = ScimMeta(
            resource_type="User",
            created=original.meta.created if original.meta else now,
            last_modified=now,
            version=_etag(now),
        )
        users[user_id] = user
        return user

    def update_user(self, tenant_id: str, user_id: str, user: ScimUser) -> ScimUser:
        users = self._t(tenant_id).users
        if user_id not in users:
            raise ScimError(404, f"user {user_id} not found")
        users[user_id] = user
        return user

    def delete_user(self, tenant_id: str, user_id: str) -> None:
        users = self._t(tenant_id).users
        if user_id not in users:
            raise ScimError(404, f"user {user_id} not found")
        del users[user_id]
        # Drop from all group memberships.
        for group in self._t(tenant_id).groups.values():
            group.members = [m for m in group.members if m.get("value") != user_id]

    # ── Groups ──
    def list_groups(
        self, tenant_id: str, filt: ScimFilter | None, start_index: int, count: int
    ) -> tuple[list[ScimGroup], int]:
        groups = list(self._t(tenant_id).groups.values())
        if filt is not None:
            groups = [g for g in groups if _match_group(g, filt)]
        groups.sort(key=lambda g: g.id)
        total = len(groups)
        page = groups[max(start_index - 1, 0) : max(start_index - 1, 0) + max(count, 0)]
        return page, total

    def get_group(self, tenant_id: str, group_id: str) -> ScimGroup | None:
        return self._t(tenant_id).groups.get(group_id)

    def create_group(self, tenant_id: str, group: ScimGroup, now: datetime) -> ScimGroup:
        groups = self._t(tenant_id).groups
        for existing in groups.values():
            if existing.display_name == group.display_name:
                raise ScimError(
                    409, f"displayName {group.display_name!r} already exists", "uniqueness"
                )
        if not group.id:
            group.id = new_group_id()
        group.meta = ScimMeta(
            resource_type="Group",
            created=now,
            last_modified=now,
            version=_etag(now),
        )
        groups[group.id] = group
        return group

    def replace_group(self, tenant_id: str, group_id: str, group: ScimGroup, now: datetime) -> ScimGroup:
        groups = self._t(tenant_id).groups
        if group_id not in groups:
            raise ScimError(404, f"group {group_id} not found")
        original = groups[group_id]
        for existing in groups.values():
            if existing.id != group_id and existing.display_name == group.display_name:
                raise ScimError(
                    409, f"displayName {group.display_name!r} already exists", "uniqueness"
                )
        group.id = group_id
        group.meta = ScimMeta(
            resource_type="Group",
            created=original.meta.created if original.meta else now,
            last_modified=now,
            version=_etag(now),
        )
        groups[group_id] = group
        return group

    def update_group(self, tenant_id: str, group_id: str, group: ScimGroup) -> ScimGroup:
        groups = self._t(tenant_id).groups
        if group_id not in groups:
            raise ScimError(404, f"group {group_id} not found")
        groups[group_id] = group
        return group

    def delete_group(self, tenant_id: str, group_id: str) -> None:
        groups = self._t(tenant_id).groups
        if group_id not in groups:
            raise ScimError(404, f"group {group_id} not found")
        del groups[group_id]


def _match_user(user: ScimUser, filt: ScimFilter) -> bool:
    if filt.attribute == "userName":
        return user.user_name == filt.value
    if filt.attribute == "externalId":
        return user.external_id == filt.value
    if filt.attribute == "id":
        return user.id == filt.value
    if filt.attribute == "active":
        return str(user.active).lower() == filt.value.lower()
    raise ScimError(400, f"filter on {filt.attribute!r} is not supported", "invalidFilter")


def _match_group(group: ScimGroup, filt: ScimFilter) -> bool:
    if filt.attribute == "displayName":
        return group.display_name == filt.value
    if filt.attribute == "id":
        return group.id == filt.value
    raise ScimError(400, f"filter on {filt.attribute!r} is not supported", "invalidFilter")

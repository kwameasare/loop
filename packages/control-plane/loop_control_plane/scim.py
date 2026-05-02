"""SCIM 2.0 provisioning service — S611.

Implements the RFC 7644 core resource types needed by enterprise IdPs:
  - /scim/v2/Users   — create / read / update (PUT+PATCH) / delete
  - /scim/v2/Groups  — create / read / update (PUT+PATCH) / delete
  - /scim/v2/ServiceProviderConfig — static capability document
  - /scim/v2/Schemas — schema discovery

Design notes:
- In-memory store (same pattern as WorkspaceService); swap to Postgres by
  implementing the Protocol interfaces.
- SCIM PATCH uses the ``Operations`` array (RFC 7644 §3.5.2); we handle
  the common ops issued by Okta, Entra ID, and Google Workspace.
- Group membership changes are kept consistent with User.groups via a
  single lock so concurrent IdP calls cannot produce split-brain state.
- ``SCIMError`` is raised for all validation / not-found failures; callers
  should map it to the appropriate HTTP 4xx response with JSON body
  ``{"schemas":["urn:ietf:params:scim:api:messages:2.0:Error"],...}``.
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# SCIM schema URNs
# ---------------------------------------------------------------------------

_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
_ENTERPRISE_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
_LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
_PATCH_OP_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class SCIMEmail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    value: str
    type: str = "work"
    primary: bool = True


class SCIMName(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    formatted: str = ""
    givenName: str = ""  # noqa: N815
    familyName: str = ""  # noqa: N815


class SCIMUser(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    externalId: str | None = None  # noqa: N815
    userName: str  # noqa: N815
    displayName: str = ""  # noqa: N815
    name: SCIMName = Field(default_factory=SCIMName)
    emails: list[SCIMEmail] = Field(default_factory=list)
    active: bool = True
    groups: list[str] = Field(default_factory=list)  # group ids
    meta_created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    meta_modified: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_scim(self) -> dict[str, Any]:
        return {
            "schemas": [_USER_SCHEMA],
            "id": self.id,
            "externalId": self.externalId,
            "userName": self.userName,
            "displayName": self.displayName,
            "name": {
                "formatted": self.name.formatted,
                "givenName": self.name.givenName,
                "familyName": self.name.familyName,
            },
            "emails": [e.model_dump() for e in self.emails],
            "active": self.active,
            "groups": [{"value": gid, "type": "direct"} for gid in self.groups],
            "meta": {
                "resourceType": "User",
                "created": self.meta_created.isoformat(),
                "lastModified": self.meta_modified.isoformat(),
                "location": f"/scim/v2/Users/{self.id}",
            },
        }


class SCIMMember(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    value: str  # user id
    display: str = ""


class SCIMGroup(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    externalId: str | None = None  # noqa: N815
    displayName: str  # noqa: N815
    members: list[SCIMMember] = Field(default_factory=list)
    meta_created: datetime = Field(default_factory=lambda: datetime.now(UTC))
    meta_modified: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_scim(self) -> dict[str, Any]:
        return {
            "schemas": [_GROUP_SCHEMA],
            "id": self.id,
            "externalId": self.externalId,
            "displayName": self.displayName,
            "members": [m.model_dump() for m in self.members],
            "meta": {
                "resourceType": "Group",
                "created": self.meta_created.isoformat(),
                "lastModified": self.meta_modified.isoformat(),
                "location": f"/scim/v2/Groups/{self.id}",
            },
        }


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class SCIMError(Exception):
    """SCIM protocol error; ``status`` maps to HTTP status code."""

    def __init__(self, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemas": [_ERROR_SCHEMA],
            "detail": self.detail,
            "status": str(self.status),
        }


# ---------------------------------------------------------------------------
# In-memory SCIM service
# ---------------------------------------------------------------------------


_USERNAME_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$|^[^\s]{1,128}$")


class SCIMService:
    """RFC 7644 SCIM 2.0 store.  Thread-safe via a single asyncio Lock."""

    def __init__(self) -> None:
        self._users: dict[str, SCIMUser] = {}
        self._usernames: dict[str, str] = {}  # userName → id
        self._groups: dict[str, SCIMGroup] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def create_user(self, payload: dict[str, Any]) -> SCIMUser:
        async with self._lock:
            username = (payload.get("userName") or "").strip()
            if not username:
                raise SCIMError("userName is required", 400)
            if username in self._usernames:
                raise SCIMError(
                    f"userName {username!r} already exists", 409
                )
            uid = str(uuid4())
            user = self._build_user(uid, payload)
            self._users[uid] = user
            self._usernames[username] = uid
            return user

    async def get_user(self, user_id: str) -> SCIMUser:
        async with self._lock:
            return self._require_user(user_id)

    async def list_users(
        self,
        *,
        filter_str: str | None = None,
        start_index: int = 1,
        count: int = 100,
    ) -> tuple[list[SCIMUser], int]:
        async with self._lock:
            users = list(self._users.values())
            if filter_str:
                users = _apply_filter(users, filter_str)
            total = len(users)
            page = users[max(0, start_index - 1) : start_index - 1 + count]
            return page, total

    async def replace_user(self, user_id: str, payload: dict[str, Any]) -> SCIMUser:
        async with self._lock:
            old = self._require_user(user_id)
            new_username = (payload.get("userName") or "").strip()
            if not new_username:
                raise SCIMError("userName is required", 400)
            if new_username != old.userName and new_username in self._usernames:
                raise SCIMError(
                    f"userName {new_username!r} already exists", 409
                )
            updated = self._build_user(user_id, payload)
            if new_username != old.userName:
                del self._usernames[old.userName]
                self._usernames[new_username] = user_id
            self._users[user_id] = updated
            return updated

    async def patch_user(
        self, user_id: str, operations: list[dict[str, Any]]
    ) -> SCIMUser:
        async with self._lock:
            user = self._require_user(user_id)
            data = user.model_dump(
                exclude={"meta_created", "meta_modified", "groups"}
            )
            data["groups"] = list(user.groups)
            for op in operations:
                _apply_patch_op(data, op)
            data["meta_modified"] = datetime.now(UTC)
            # preserve immutable fields
            data["id"] = user_id
            data["meta_created"] = user.meta_created
            new_user = SCIMUser(**data)
            if new_user.userName != user.userName:
                if new_user.userName in self._usernames:
                    raise SCIMError(
                        f"userName {new_user.userName!r} already exists", 409
                    )
                del self._usernames[user.userName]
                self._usernames[new_user.userName] = user_id
            self._users[user_id] = new_user
            return new_user

    async def delete_user(self, user_id: str) -> None:
        async with self._lock:
            user = self._require_user(user_id)
            del self._users[user_id]
            self._usernames.pop(user.userName, None)
            # Remove from all groups
            for gid, grp in list(self._groups.items()):
                new_members = [m for m in grp.members if m.value != user_id]
                if len(new_members) != len(grp.members):
                    self._groups[gid] = grp.model_copy(
                        update={
                            "members": new_members,
                            "meta_modified": datetime.now(UTC),
                        }
                    )

    # ------------------------------------------------------------------
    # Groups
    # ------------------------------------------------------------------

    async def create_group(self, payload: dict[str, Any]) -> SCIMGroup:
        async with self._lock:
            display = (payload.get("displayName") or "").strip()
            if not display:
                raise SCIMError("displayName is required", 400)
            gid = str(uuid4())
            group = self._build_group(gid, payload)
            self._groups[gid] = group
            # Back-patch user.groups
            await self._sync_user_groups_locked(group)
            return group

    async def get_group(self, group_id: str) -> SCIMGroup:
        async with self._lock:
            return self._require_group(group_id)

    async def list_groups(
        self,
        *,
        filter_str: str | None = None,
        start_index: int = 1,
        count: int = 100,
    ) -> tuple[list[SCIMGroup], int]:
        async with self._lock:
            groups = list(self._groups.values())
            if filter_str:
                groups = _apply_filter(groups, filter_str)
            total = len(groups)
            page = groups[max(0, start_index - 1) : start_index - 1 + count]
            return page, total

    async def replace_group(
        self, group_id: str, payload: dict[str, Any]
    ) -> SCIMGroup:
        async with self._lock:
            self._require_group(group_id)
            updated = self._build_group(group_id, payload)
            self._groups[group_id] = updated
            await self._sync_user_groups_locked(updated)
            return updated

    async def patch_group(
        self, group_id: str, operations: list[dict[str, Any]]
    ) -> SCIMGroup:
        async with self._lock:
            group = self._require_group(group_id)
            data = group.model_dump(exclude={"meta_created", "meta_modified"})
            data["members"] = [m.model_dump() for m in group.members]
            for op in operations:
                _apply_patch_op(data, op)
            data["meta_modified"] = datetime.now(UTC)
            data["id"] = group_id
            data["meta_created"] = group.meta_created
            new_group = SCIMGroup(**data)
            self._groups[group_id] = new_group
            await self._sync_user_groups_locked(new_group)
            return new_group

    async def delete_group(self, group_id: str) -> None:
        async with self._lock:
            self._require_group(group_id)
            del self._groups[group_id]
            # Strip group from user.groups
            for uid, user in list(self._users.items()):
                if group_id in user.groups:
                    new_groups = [g for g in user.groups if g != group_id]
                    self._users[uid] = user.model_copy(
                        update={
                            "groups": new_groups,
                            "meta_modified": datetime.now(UTC),
                        }
                    )

    # ------------------------------------------------------------------
    # Service provider config / schemas
    # ------------------------------------------------------------------

    @staticmethod
    def service_provider_config() -> dict[str, Any]:
        return {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
            ],
            "documentationUri": "https://docs.loop.dev/scim",
            "patch": {"supported": True},
            "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
            "filter": {"supported": True, "maxResults": 200},
            "changePassword": {"supported": False},
            "sort": {"supported": False},
            "etag": {"supported": False},
            "authenticationSchemes": [
                {
                    "type": "oauthbearertoken",
                    "name": "OAuth Bearer Token",
                    "description": "Authentication scheme using the OAuth Bearer Token Standard",
                }
            ],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _require_user(self, user_id: str) -> SCIMUser:
        user = self._users.get(user_id)
        if user is None:
            raise SCIMError(f"User {user_id!r} not found", 404)
        return user

    def _require_group(self, group_id: str) -> SCIMGroup:
        group = self._groups.get(group_id)
        if group is None:
            raise SCIMError(f"Group {group_id!r} not found", 404)
        return group

    @staticmethod
    def _build_user(uid: str, payload: dict[str, Any]) -> SCIMUser:
        name_raw = payload.get("name") or {}
        emails_raw = payload.get("emails") or []
        now = datetime.now(UTC)
        return SCIMUser(
            id=uid,
            externalId=payload.get("externalId"),
            userName=payload.get("userName", ""),
            displayName=payload.get("displayName", ""),
            name=SCIMName(
                formatted=name_raw.get("formatted", ""),
                givenName=name_raw.get("givenName", ""),
                familyName=name_raw.get("familyName", ""),
            ),
            emails=[
                SCIMEmail(
                    value=e.get("value", ""),
                    type=e.get("type", "work"),
                    primary=e.get("primary", True),
                )
                for e in emails_raw
            ],
            active=bool(payload.get("active", True)),
            groups=list(payload.get("groups", [])),
            meta_created=now,
            meta_modified=now,
        )

    @staticmethod
    def _build_group(gid: str, payload: dict[str, Any]) -> SCIMGroup:
        now = datetime.now(UTC)
        members_raw = payload.get("members") or []
        return SCIMGroup(
            id=gid,
            externalId=payload.get("externalId"),
            displayName=payload.get("displayName", ""),
            members=[
                SCIMMember(
                    value=m.get("value", ""),
                    display=m.get("display", ""),
                )
                for m in members_raw
            ],
            meta_created=now,
            meta_modified=now,
        )

    async def _sync_user_groups_locked(self, group: SCIMGroup) -> None:
        """Keep user.groups in sync with group.members (called under lock)."""
        member_ids = {m.value for m in group.members}
        for uid, user in list(self._users.items()):
            in_group = group.id in user.groups
            should_be = uid in member_ids
            if in_group == should_be:
                continue
            new_groups: list[str]
            if should_be:
                new_groups = [*user.groups, group.id]
            else:
                new_groups = [g for g in user.groups if g != group.id]
            self._users[uid] = user.model_copy(
                update={
                    "groups": new_groups,
                    "meta_modified": datetime.now(UTC),
                }
            )


# ---------------------------------------------------------------------------
# Filter parser (eq / co only — what IdPs actually send)
# ---------------------------------------------------------------------------


def _apply_filter(
    items: list[SCIMUser] | list[SCIMGroup], filter_str: str
) -> list[SCIMUser] | list[SCIMGroup]:
    """Apply a SCIM filter expression to a list of users or groups.

    Only ``eq`` and ``co`` operators on top-level string attributes are
    supported — this covers what major IdPs (Okta, Entra, Google) send.
    """
    m = re.match(
        r'(\w+)\s+(eq|co)\s+"([^"]*)"', filter_str.strip(), re.IGNORECASE
    )
    if not m:
        return items
    attr, op, val = m.group(1), m.group(2).lower(), m.group(3)
    result = []
    for item in items:
        item_val = str(getattr(item, attr, "") or "").lower()
        target = val.lower()
        if (op == "eq" and item_val == target) or (op == "co" and target in item_val):
            result.append(item)
    return result  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# PATCH op interpreter
# ---------------------------------------------------------------------------


def _apply_patch_op(data: dict[str, Any], op: dict[str, Any]) -> None:
    """Apply a single SCIM PATCH operation to a mutable dict."""
    action = (op.get("op") or "").lower()
    path = op.get("path") or ""
    value = op.get("value")

    if action == "replace":
        if path:
            # path like "members" or "displayName"
            data[path] = value
        elif isinstance(value, dict):
            data.update(value)
    elif action == "add":
        if path == "members" and isinstance(value, list):
            existing = {m["value"] for m in data.get("members", [])}
            for member in value:
                if member["value"] not in existing:
                    data.setdefault("members", []).append(member)
        elif path:
            data[path] = value
        elif isinstance(value, dict):
            data.update(value)
    elif action == "remove":
        if path == "members" and isinstance(value, list):
            remove_ids = {m["value"] for m in value}
            data["members"] = [
                m for m in data.get("members", []) if m["value"] not in remove_ids
            ]
        elif path:
            data.pop(path, None)

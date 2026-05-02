"""SCIM 2.0 protocol primitives (S611).

Implements RFC 7643 (resources) + RFC 7644 (protocol) for the
**provisioning side** of Loop's SSO. The OpenAPI surface lives in
``loop_implementation/api/openapi.yaml`` under tag ``SCIM``; this
module is the in-process logic the cp-api adapter calls into.

Scope of this module:

* :class:`ScimUser`, :class:`ScimGroup`, :class:`ScimMeta` —
  RFC 7643 resources (a pragmatic subset; ``additionalProperties``
  on the wire mean we tolerate vendor-extension URNs without
  ``schemas`` whitelisting).
* :class:`ScimPatchOp` + :func:`apply_patch_op` — RFC 7644 §3.5.2
  add/replace/remove against a User or Group.
* :func:`parse_scim_filter` — the ``filter=`` query subset we
  support (``eq`` only, on top-level attributes). Sufficient for
  Okta, Entra, and Google Workspace IdPs; richer filters raise
  :class:`ScimError(scimType="invalidFilter")`.
* :class:`ScimStore` Protocol — the persistence boundary (see
  :mod:`loop_control_plane.scim_store` for the in-memory impl).
* :func:`apply_user_request` / :func:`apply_group_request` — the
  REST verb dispatcher used by the cp-api adapter.

Cross-cutting concerns (bearer-token auth, audit events) live in
the adapter; this module is pure domain logic so it stays unit-
testable without an HTTP layer.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Any, Literal, Protocol


# ── RFC 7644 §3.12 / §3.4.2.2 schema URNs we care about ──────────
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
PATCH_OP_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
SP_CONFIG_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"


ScimType = Literal[
    "invalidFilter",
    "tooMany",
    "uniqueness",
    "mutability",
    "invalidSyntax",
    "invalidPath",
    "noTarget",
    "invalidValue",
    "invalidVers",
    "sensitive",
]


class ScimError(Exception):
    """RFC 7644 §3.12 typed protocol error.

    The cp-api adapter renders this as JSON of shape::

        {"schemas": [ERROR_SCHEMA], "status": "404",
         "scimType": "invalidFilter", "detail": "..."}
    """

    def __init__(self, status: int, detail: str, scim_type: ScimType | None = None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.scim_type = scim_type

    def to_resource(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schemas": [ERROR_SCHEMA],
            "status": str(self.status),
            "detail": self.detail,
        }
        if self.scim_type is not None:
            body["scimType"] = self.scim_type
        return body


# ── Resource models ──────────────────────────────────────────────


@dataclass(slots=True)
class ScimMeta:
    resource_type: str
    created: datetime
    last_modified: datetime
    version: str

    def to_resource(self) -> dict[str, Any]:
        return {
            "resourceType": self.resource_type,
            "created": _iso(self.created),
            "lastModified": _iso(self.last_modified),
            "version": self.version,
        }


@dataclass(slots=True)
class ScimUser:
    user_name: str
    id: str = ""
    external_id: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    emails: list[dict[str, Any]] = field(default_factory=list)
    active: bool = True
    groups: list[dict[str, Any]] = field(default_factory=list)
    """Read-only on the wire (managed via Group.members)."""
    meta: ScimMeta | None = None

    def to_resource(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schemas": [USER_SCHEMA],
            "id": self.id,
            "userName": self.user_name,
            "active": self.active,
        }
        if self.external_id is not None:
            body["externalId"] = self.external_id
        if self.given_name or self.family_name:
            body["name"] = {
                k: v
                for k, v in (
                    ("givenName", self.given_name),
                    ("familyName", self.family_name),
                )
                if v
            }
        if self.emails:
            body["emails"] = self.emails
        if self.groups:
            body["groups"] = self.groups
        if self.meta is not None:
            body["meta"] = self.meta.to_resource()
        return body


@dataclass(slots=True)
class ScimGroup:
    display_name: str
    id: str = ""
    members: list[dict[str, Any]] = field(default_factory=list)
    meta: ScimMeta | None = None

    def to_resource(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schemas": [GROUP_SCHEMA],
            "id": self.id,
            "displayName": self.display_name,
            "members": self.members,
        }
        if self.meta is not None:
            body["meta"] = self.meta.to_resource()
        return body


@dataclass(frozen=True, slots=True)
class ScimPatchOperation:
    op: Literal["add", "replace", "remove"]
    path: str | None
    value: Any


@dataclass(frozen=True, slots=True)
class ScimPatchOp:
    operations: tuple[ScimPatchOperation, ...]


# ── Parsing ──────────────────────────────────────────────────────


def parse_user(payload: dict[str, Any]) -> ScimUser:
    if not isinstance(payload, dict):
        raise ScimError(400, "request body must be a JSON object", "invalidSyntax")
    user_name = payload.get("userName")
    if not user_name or not isinstance(user_name, str):
        raise ScimError(400, "userName is required", "invalidValue")
    name = payload.get("name") or {}
    if not isinstance(name, dict):
        raise ScimError(400, "name must be an object", "invalidValue")
    emails = payload.get("emails") or []
    if not isinstance(emails, list):
        raise ScimError(400, "emails must be an array", "invalidValue")
    return ScimUser(
        user_name=user_name,
        id=str(payload.get("id") or ""),
        external_id=payload.get("externalId"),
        given_name=name.get("givenName"),
        family_name=name.get("familyName"),
        emails=list(emails),
        active=bool(payload.get("active", True)),
    )


def parse_group(payload: dict[str, Any]) -> ScimGroup:
    if not isinstance(payload, dict):
        raise ScimError(400, "request body must be a JSON object", "invalidSyntax")
    display_name = payload.get("displayName")
    if not display_name or not isinstance(display_name, str):
        raise ScimError(400, "displayName is required", "invalidValue")
    members = payload.get("members") or []
    if not isinstance(members, list):
        raise ScimError(400, "members must be an array", "invalidValue")
    return ScimGroup(
        display_name=display_name,
        id=str(payload.get("id") or ""),
        members=list(members),
    )


def parse_patch_op(payload: dict[str, Any]) -> ScimPatchOp:
    if not isinstance(payload, dict):
        raise ScimError(400, "request body must be a JSON object", "invalidSyntax")
    ops_raw = payload.get("Operations")
    if not isinstance(ops_raw, list) or not ops_raw:
        raise ScimError(400, "Operations must be a non-empty array", "invalidSyntax")
    ops: list[ScimPatchOperation] = []
    for raw in ops_raw:
        if not isinstance(raw, dict):
            raise ScimError(400, "operation must be an object", "invalidSyntax")
        op = str(raw.get("op", "")).lower()
        if op not in ("add", "replace", "remove"):
            raise ScimError(400, f"unsupported op {op!r}", "invalidValue")
        ops.append(
            ScimPatchOperation(
                op=op,  # type: ignore[arg-type]
                path=raw.get("path"),
                value=raw.get("value"),
            )
        )
    return ScimPatchOp(operations=tuple(ops))


# ── Filter parsing (RFC 7644 §3.4.2.2 — eq only) ─────────────────


_FILTER_RE = re.compile(
    r"""^\s*
        (?P<attr>[A-Za-z][A-Za-z0-9_.\-]*)
        \s+(?P<op>eq)\s+
        "(?P<value>(?:[^"\\]|\\.)*)"
        \s*$""",
    re.VERBOSE,
)


@dataclass(frozen=True, slots=True)
class ScimFilter:
    attribute: str
    value: str


def parse_scim_filter(expr: str | None) -> ScimFilter | None:
    """Parse the SCIM ``filter=`` query value. Returns ``None`` for
    no filter; raises :class:`ScimError` for unsupported syntax."""
    if expr is None or not expr.strip():
        return None
    m = _FILTER_RE.match(expr)
    if not m:
        raise ScimError(
            400,
            "only 'attr eq \"value\"' filters are supported",
            "invalidFilter",
        )
    return ScimFilter(attribute=m.group("attr"), value=m.group("value").replace('\\"', '"'))


# ── PatchOp execution ────────────────────────────────────────────


# Subset of attribute paths PatchOp can target. RFC 7644 §3.5.2.1
# allows complex paths; we accept the ones Okta/Entra send.
_USER_PATCH_ATTRS = {
    "active": "active",
    "userName": "user_name",
    "externalId": "external_id",
    "name.givenName": "given_name",
    "name.familyName": "family_name",
}


def apply_patch_to_user(user: ScimUser, patch: ScimPatchOp, now: datetime) -> ScimUser:
    """Apply a PatchOp to a user. Returns a new user; raises on
    invalid path or noTarget."""
    updated = replace(user)
    for op in patch.operations:
        path = op.path
        if path is None and op.op == "replace" and isinstance(op.value, dict):
            # Okta convention: {"op": "replace", "value": {"active": false}}
            for k, v in op.value.items():
                _set_user_attr(updated, k, v, op.op)
            continue
        if path is None:
            raise ScimError(400, f"{op.op} requires a path", "invalidPath")
        if op.op == "remove":
            _set_user_attr(updated, path, None, "remove")
            continue
        _set_user_attr(updated, path, op.value, op.op)
    if updated.meta is not None:
        updated.meta = ScimMeta(
            resource_type=updated.meta.resource_type,
            created=updated.meta.created,
            last_modified=now,
            version=_etag(now),
        )
    return updated


def _set_user_attr(user: ScimUser, path: str, value: Any, op: str) -> None:
    field_name = _USER_PATCH_ATTRS.get(path)
    if field_name is None:
        raise ScimError(400, f"unsupported user attribute path {path!r}", "invalidPath")
    if op == "remove":
        if field_name == "active":
            user.active = False
            return
        setattr(user, field_name, None)
        return
    if field_name == "active":
        user.active = bool(value)
        return
    setattr(user, field_name, value)


def apply_patch_to_group(group: ScimGroup, patch: ScimPatchOp, now: datetime) -> ScimGroup:
    """Apply a PatchOp to a group, including ``members`` add/remove
    (the common case for Okta SCIM)."""
    members = list(group.members)
    display = group.display_name
    for op in patch.operations:
        path = op.path
        if path == "displayName":
            if op.op == "remove":
                raise ScimError(400, "cannot remove displayName", "mutability")
            if not isinstance(op.value, str) or not op.value:
                raise ScimError(400, "displayName must be a non-empty string", "invalidValue")
            display = op.value
            continue
        if path == "members" or path is None:
            value_list = _members_value(op.value)
            if op.op == "add":
                # Idempotent add: skip duplicates by value.
                existing_values = {m.get("value") for m in members}
                for m in value_list:
                    if m.get("value") not in existing_values:
                        members.append(m)
                        existing_values.add(m.get("value"))
            elif op.op == "replace":
                members = list(value_list)
            elif op.op == "remove":
                if value_list:
                    drop = {m.get("value") for m in value_list}
                    members = [m for m in members if m.get("value") not in drop]
                else:
                    members = []
            continue
        if path.startswith('members[') and op.op == "remove":
            # Okta filter-form remove: members[value eq "u-1"]
            target = _extract_member_id_filter(path)
            members = [m for m in members if m.get("value") != target]
            continue
        raise ScimError(400, f"unsupported group attribute path {path!r}", "invalidPath")
    updated = ScimGroup(display_name=display, id=group.id, members=members, meta=group.meta)
    if updated.meta is not None:
        updated.meta = ScimMeta(
            resource_type=updated.meta.resource_type,
            created=updated.meta.created,
            last_modified=now,
            version=_etag(now),
        )
    return updated


def _members_value(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict):
                out.append(item)
            else:
                raise ScimError(400, "members entries must be objects", "invalidValue")
        return out
    raise ScimError(400, "members value must be an object or array", "invalidValue")


_MEMBER_FILTER_RE = re.compile(r'members\[\s*value\s+eq\s+"([^"]+)"\s*\]')


def _extract_member_id_filter(path: str) -> str:
    m = _MEMBER_FILTER_RE.match(path)
    if not m:
        raise ScimError(400, f"unsupported member filter {path!r}", "invalidPath")
    return m.group(1)


# ── Store boundary ───────────────────────────────────────────────


class ScimStore(Protocol):
    """The persistence boundary. The in-memory impl in
    :mod:`loop_control_plane.scim_store` is used by tests; the
    production impl lives in cp-api against Postgres."""

    def list_users(
        self, tenant_id: str, filt: ScimFilter | None, start_index: int, count: int
    ) -> tuple[list[ScimUser], int]: ...
    def get_user(self, tenant_id: str, user_id: str) -> ScimUser | None: ...
    def create_user(self, tenant_id: str, user: ScimUser, now: datetime) -> ScimUser: ...
    def replace_user(self, tenant_id: str, user_id: str, user: ScimUser, now: datetime) -> ScimUser: ...
    def update_user(self, tenant_id: str, user_id: str, user: ScimUser) -> ScimUser: ...
    def delete_user(self, tenant_id: str, user_id: str) -> None: ...

    def list_groups(
        self, tenant_id: str, filt: ScimFilter | None, start_index: int, count: int
    ) -> tuple[list[ScimGroup], int]: ...
    def get_group(self, tenant_id: str, group_id: str) -> ScimGroup | None: ...
    def create_group(self, tenant_id: str, group: ScimGroup, now: datetime) -> ScimGroup: ...
    def replace_group(self, tenant_id: str, group_id: str, group: ScimGroup, now: datetime) -> ScimGroup: ...
    def update_group(self, tenant_id: str, group_id: str, group: ScimGroup) -> ScimGroup: ...
    def delete_group(self, tenant_id: str, group_id: str) -> None: ...


# ── Helpers ──────────────────────────────────────────────────────


def _iso(d: datetime) -> str:
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _etag(now: datetime) -> str:
    return f"W/\"{int(now.timestamp())}\""


def new_user_id() -> str:
    return f"u-{uuid.uuid4().hex[:12]}"


def new_group_id() -> str:
    return f"g-{uuid.uuid4().hex[:12]}"


def list_response(resources: list[dict[str, Any]], total: int, start_index: int) -> dict[str, Any]:
    return {
        "schemas": [LIST_RESPONSE_SCHEMA],
        "totalResults": total,
        "startIndex": start_index,
        "itemsPerPage": len(resources),
        "Resources": resources,
    }


# ── Service-provider config (RFC 7644 §4) ────────────────────────


def service_provider_config() -> dict[str, Any]:
    """The static capability advertisement Loop returns at
    ``/scim/v2/{tenant_id}/ServiceProviderConfig``. Bulk + sort are
    intentionally false; PATCH + ETag + filter are supported."""
    return {
        "schemas": [SP_CONFIG_SCHEMA],
        "documentationUri": "https://docs.loop.dev/scim",
        "patch": {"supported": True},
        "bulk": {"supported": False, "maxOperations": 0, "maxPayloadSize": 0},
        "filter": {"supported": True, "maxResults": 200},
        "changePassword": {"supported": False},
        "sort": {"supported": False},
        "etag": {"supported": True},
        "authenticationSchemes": [
            {
                "type": "oauthbearertoken",
                "name": "OAuth Bearer Token",
                "description": "Tenant-scoped SCIM token minted in Studio → Settings → SSO.",
                "specUri": "https://datatracker.ietf.org/doc/html/rfc6750",
                "documentationUri": "https://docs.loop.dev/scim/auth",
            }
        ],
    }

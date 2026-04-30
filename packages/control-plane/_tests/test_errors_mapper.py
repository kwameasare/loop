"""Tests for the LOOP-API error mapper (S118)."""

from __future__ import annotations

from loop_control_plane.api_keys import ApiKeyError
from loop_control_plane.auth import AuthError
from loop_control_plane.authorize import AuthorisationError
from loop_control_plane.errors import (
    CODE_FORBIDDEN,
    CODE_INTERNAL,
    CODE_NOT_FOUND,
    CODE_TOKEN_INVALID,
    CODE_VALIDATION,
    LoopApiError,
    map_to_loop_api_error,
)
from loop_control_plane.workspaces import WorkspaceError


def test_validation_error_maps_to_400() -> None:
    err = map_to_loop_api_error(WorkspaceError("name too long"), request_id="r1")
    assert (err.code, err.status) == CODE_VALIDATION


def test_unknown_workspace_maps_to_404() -> None:
    err = map_to_loop_api_error(WorkspaceError("unknown workspace: x"), request_id="r")
    assert (err.code, err.status) == CODE_NOT_FOUND


def test_auth_error_maps_to_401() -> None:
    err = map_to_loop_api_error(AuthError("token expired"), request_id="r")
    assert (err.code, err.status) == CODE_TOKEN_INVALID


def test_authorisation_error_maps_to_403() -> None:
    err = map_to_loop_api_error(AuthorisationError("nope"), request_id="r")
    assert (err.code, err.status) == CODE_FORBIDDEN


def test_api_key_unknown_maps_to_404() -> None:
    err = map_to_loop_api_error(ApiKeyError("unknown key"), request_id="r")
    assert (err.code, err.status) == CODE_NOT_FOUND


def test_api_key_revoked_maps_to_401() -> None:
    err = map_to_loop_api_error(ApiKeyError("key revoked"), request_id="r")
    assert (err.code, err.status) == CODE_TOKEN_INVALID


def test_api_key_validation_maps_to_400() -> None:
    err = map_to_loop_api_error(ApiKeyError("name too short"), request_id="r")
    assert (err.code, err.status) == CODE_VALIDATION


def test_unknown_exception_maps_to_500() -> None:
    err = map_to_loop_api_error(RuntimeError("disk on fire"), request_id="r")
    assert (err.code, err.status) == CODE_INTERNAL


def test_envelope_serialises_to_dict() -> None:
    err = LoopApiError(code="LOOP-API-001", message="m", status=400, request_id="r")
    body = err.to_dict()
    assert body == {
        "code": "LOOP-API-001",
        "message": "m",
        "status": 400,
        "request_id": "r",
    }


def test_request_id_is_echoed() -> None:
    err = map_to_loop_api_error(WorkspaceError("x"), request_id="abcdef")
    assert err.request_id == "abcdef"

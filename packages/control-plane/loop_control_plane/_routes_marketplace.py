"""Marketplace browse routes for Studio."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from loop_control_plane._app_common import CALLER
from loop_control_plane.mcp_marketplace import MarketplaceBrowser

router = APIRouter(prefix="/v1/marketplace", tags=["Marketplace"])


@router.get("")
async def browse_marketplace(
    request: Request,
    q: str = Query(default=""),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    caller_sub: str = CALLER,
) -> dict[str, Any]:
    # ``caller_sub`` ensures the auth dependency runs even though the first-party
    # catalog itself is workspace-neutral.
    _ = caller_sub
    browser = MarketplaceBrowser(store=request.app.state.cp.marketplace_store)
    items = browser.browse(query=q, category=category, limit=limit)
    return {"items": [item.model_dump(mode="json") for item in items]}


__all__ = ["router"]

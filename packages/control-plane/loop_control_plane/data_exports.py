"""Data-export loading contracts for cp-api."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol
from uuid import UUID


class DataExportStore(Protocol):
    async def load_workspace_export(
        self,
        *,
        workspace_id: UUID,
        export_id: str,
        region: str,
    ) -> Mapping[str, Any]: ...

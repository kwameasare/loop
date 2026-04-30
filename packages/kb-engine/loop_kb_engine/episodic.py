"""Episodic memory collection schema (S490).

Per ADR / SCHEMA.md: each agent gets its own Qdrant collection, distinct
from the workspace KB collection. Naming + payload schema is fixed here
so the data-plane writer and the agent reader can never disagree.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EPISODIC_COLLECTION_PREFIX = "episodic"
EPISODIC_DEFAULT_DIMENSIONS = 1024
EPISODIC_DEFAULT_DISTANCE = "Cosine"

_AGENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")

#: Required payload keys on every episodic point. Documented in SCHEMA.md.
EPISODIC_PAYLOAD_KEYS: tuple[str, ...] = (
    "agent_id",
    "workspace_id",
    "conversation_id",
    "turn_no",
    "speaker",          # "user" | "agent" | "tool"
    "occurred_at",      # iso-8601 utc
    "salience",         # float in [0, 1]
    "summary",          # short text used for retrieval
)


def collection_name(agent_id: str) -> str:
    """Return the Qdrant collection name for an agent.

    The agent_id is validated to a slug-like grammar so collection names
    are always Qdrant-safe (no spaces, dots, slashes, or upper-case).
    """
    if not _AGENT_ID_RE.match(agent_id):
        raise ValueError(
            f"agent_id {agent_id!r} is not a valid slug ([a-z0-9][a-z0-9-]{{0,62}})"
        )
    return f"{EPISODIC_COLLECTION_PREFIX}_{agent_id}"


@dataclass(frozen=True, slots=True)
class EpisodicCollectionConfig:
    """Qdrant collection-config descriptor for episodic memory."""

    agent_id: str
    dimensions: int = EPISODIC_DEFAULT_DIMENSIONS
    distance: str = EPISODIC_DEFAULT_DISTANCE
    on_disk_payload: bool = True

    def __post_init__(self) -> None:
        if self.dimensions < 1:
            raise ValueError("dimensions must be >=1")
        if self.distance not in ("Cosine", "Dot", "Euclid"):
            raise ValueError(f"distance {self.distance!r} not supported by Qdrant")
        # Validate the agent_id by piggy-backing on collection_name().
        collection_name(self.agent_id)

    @property
    def collection_name(self) -> str:
        return collection_name(self.agent_id)

    def to_create_payload(self) -> dict[str, object]:
        """Render the body for ``PUT /collections/{name}`` (Qdrant REST)."""
        return {
            "vectors": {
                "size": self.dimensions,
                "distance": self.distance,
            },
            "on_disk_payload": self.on_disk_payload,
        }


__all__ = [
    "EPISODIC_COLLECTION_PREFIX",
    "EPISODIC_DEFAULT_DIMENSIONS",
    "EPISODIC_DEFAULT_DISTANCE",
    "EPISODIC_PAYLOAD_KEYS",
    "EpisodicCollectionConfig",
    "collection_name",
]

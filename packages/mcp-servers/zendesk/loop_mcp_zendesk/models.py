"""Strict pydantic models for the Zendesk surface."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class User(_StrictModel):
    id: int
    name: str = Field(min_length=1)
    email: str | None = None
    role: str = "end-user"


class Comment(_StrictModel):
    id: int = 0
    author_id: int
    body: str
    public: bool = True


class Ticket(_StrictModel):
    id: int = 0
    subject: str = Field(min_length=1)
    description: str = ""
    requester_id: int
    assignee_id: int | None = None
    status: str = "new"           # new | open | pending | hold | solved | closed
    priority: str = "normal"      # low | normal | high | urgent
    tags: tuple[str, ...] = ()
    comments: tuple[Comment, ...] = ()

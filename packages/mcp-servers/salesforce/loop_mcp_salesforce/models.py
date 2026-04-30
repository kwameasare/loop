"""Strict pydantic models for the slice of Salesforce we expose."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Account(_StrictModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    industry: str | None = None
    annual_revenue: float | None = None


class Contact(_StrictModel):
    id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: str | None = None
    title: str | None = None


class Opportunity(_StrictModel):
    id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    amount: float | None = None
    is_closed: bool = False
    is_won: bool = False


class Case(_StrictModel):
    id: str = ""
    account_id: str = Field(min_length=1)
    contact_id: str | None = None
    subject: str = Field(min_length=1)
    description: str = ""
    priority: str = "Medium"
    status: str = "New"

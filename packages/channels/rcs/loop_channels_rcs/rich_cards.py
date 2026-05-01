"""RCS rich-card renderer."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class RcsCardAction(StrEnum):
    DIAL = "dial"
    OPEN_URL = "open_url"
    REPLY = "reply"


class RcsSuggestion(_StrictModel):
    text: str = Field(min_length=1, max_length=25)
    action: RcsCardAction = RcsCardAction.REPLY
    payload: str


class RcsRichCard(_StrictModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2_000)
    image_url: str | None = None
    suggestions: tuple[RcsSuggestion, ...] = ()


def render_rich_card(card: RcsRichCard) -> dict[str, object]:
    content: dict[str, object] = {
        "title": card.title,
        "description": card.description,
    }
    if card.image_url is not None:
        content["media"] = {
            "height": "MEDIUM",
            "contentInfo": {"fileUrl": card.image_url},
        }
    payload: dict[str, object] = {
        "richCard": {"standaloneCard": {"cardContent": content}}
    }
    if card.suggestions:
        payload["suggestions"] = [_render_suggestion(suggestion) for suggestion in card.suggestions]
    return payload


def _render_suggestion(suggestion: RcsSuggestion) -> dict[str, object]:
    if suggestion.action is RcsCardAction.REPLY:
        return {"reply": {"text": suggestion.text, "postbackData": suggestion.payload}}
    if suggestion.action is RcsCardAction.OPEN_URL:
        return {
            "action": {
                "text": suggestion.text,
                "postbackData": suggestion.payload,
                "openUrlAction": {"url": suggestion.payload},
            }
        }
    return {
        "action": {
            "text": suggestion.text,
            "postbackData": suggestion.payload,
            "dialAction": {"phoneNumber": suggestion.payload},
        }
    }


__all__ = ["RcsCardAction", "RcsRichCard", "RcsSuggestion", "render_rich_card"]

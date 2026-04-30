"""Tests for whatsapp pass8: structured-output rendering + replay (S343/S349)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_channels_core import OutboundFrame, OutboundFrameKind
from loop_channels_whatsapp.messages import (
    InteractiveKind,
    ListRow,
    ListSection,
    ReplyButton,
    WhatsAppRenderError,
    render_interactive,
    to_messages,
)

# ---- frame path (text/handoff/error) ----------------------------------------


def _frame(kind: OutboundFrameKind, *, text: str = "", payload: dict[str, str] | None = None) -> OutboundFrame:
    return OutboundFrame(
        conversation_id=uuid4(),
        kind=kind,
        text=text,
        payload=payload or {},
        sequence=0,
    )


def test_render_text_message() -> None:
    body = to_messages(_frame(OutboundFrameKind.AGENT_MESSAGE, text="hello"), to="123")
    assert body == {
        "messaging_product": "whatsapp",
        "to": "123",
        "type": "text",
        "text": {"body": "hello"},
    }


def test_render_handoff_uses_target() -> None:
    body = to_messages(
        _frame(OutboundFrameKind.HANDOFF, payload={"target": "billing"}),
        to="123",
    )
    assert body["text"]["body"] == "Handing off to billing."


def test_render_error_includes_code() -> None:
    body = to_messages(
        _frame(OutboundFrameKind.ERROR, text="boom", payload={"code": "X"}),
        to="123",
    )
    assert body["text"]["body"] == "[X] boom"


def test_render_token_emits_empty_dict() -> None:
    body = to_messages(_frame(OutboundFrameKind.AGENT_TOKEN, text="t"), to="123")
    assert body == {}


# ---- interactive: buttons (S343) -------------------------------------------


def test_render_buttons_basic() -> None:
    body = render_interactive(
        InteractiveKind.BUTTON,
        to="123",
        body="Pick one",
        buttons=[ReplyButton(id="yes", title="Yes"), ReplyButton(id="no", title="No")],
    )
    assert body["type"] == "interactive"
    assert body["interactive"]["type"] == "button"
    buttons = body["interactive"]["action"]["buttons"]
    assert len(buttons) == 2
    assert buttons[0]["reply"]["id"] == "yes"


def test_render_buttons_truncates_title() -> None:
    body = render_interactive(
        InteractiveKind.BUTTON,
        to="123",
        body="x",
        buttons=[ReplyButton(id="a", title="x" * 100)],
    )
    assert len(body["interactive"]["action"]["buttons"][0]["reply"]["title"]) == 20


def test_render_buttons_rejects_too_many() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(
            InteractiveKind.BUTTON,
            to="1",
            body="x",
            buttons=[
                ReplyButton(id="a", title="A"),
                ReplyButton(id="b", title="B"),
                ReplyButton(id="c", title="C"),
                ReplyButton(id="d", title="D"),
            ],
        )


def test_render_buttons_rejects_empty() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(InteractiveKind.BUTTON, to="1", body="x", buttons=[])


# ---- interactive: list ------------------------------------------------------


def test_render_list_basic() -> None:
    body = render_interactive(
        InteractiveKind.LIST,
        to="123",
        body="Choose a service",
        button="Open",
        sections=[
            ListSection(
                title="Common",
                rows=(
                    ListRow(id="r1", title="Sales", description="Talk to sales"),
                    ListRow(id="r2", title="Support"),
                ),
            )
        ],
    )
    assert body["interactive"]["type"] == "list"
    assert body["interactive"]["action"]["button"] == "Open"
    rows = body["interactive"]["action"]["sections"][0]["rows"]
    assert rows[0]["description"] == "Talk to sales"
    assert "description" not in rows[1]


def test_render_list_rejects_empty_section() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(
            InteractiveKind.LIST,
            to="1",
            body="x",
            button="ok",
            sections=[ListSection(title="t", rows=())],
        )


def test_render_list_rejects_no_sections() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(InteractiveKind.LIST, to="1", body="x", sections=[])


# ---- interactive: media -----------------------------------------------------


def test_render_media_image_with_caption() -> None:
    body = render_interactive(
        InteractiveKind.MEDIA,
        to="123",
        media_type="image",
        url="https://cdn.example/img.jpg",
        caption="hello",
    )
    assert body["type"] == "image"
    assert body["image"] == {
        "link": "https://cdn.example/img.jpg",
        "caption": "hello",
    }


def test_render_media_rejects_bad_type() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(
            InteractiveKind.MEDIA, to="1", media_type="gif", url="x"
        )


def test_render_media_rejects_empty_url() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(InteractiveKind.MEDIA, to="1", media_type="image", url="")


# ---- interactive: template --------------------------------------------------


def test_render_template_default_language() -> None:
    body = render_interactive(
        InteractiveKind.TEMPLATE, to="123", name="welcome"
    )
    assert body["template"]["language"]["code"] == "en_US"
    assert body["template"]["name"] == "welcome"


def test_render_template_with_components() -> None:
    body = render_interactive(
        InteractiveKind.TEMPLATE,
        to="123",
        name="otp",
        language="fr_FR",
        components=[{"type": "body", "parameters": [{"type": "text", "text": "1234"}]}],
    )
    assert body["template"]["language"]["code"] == "fr_FR"
    assert body["template"]["components"][0]["type"] == "body"


def test_render_template_rejects_empty_name() -> None:
    with pytest.raises(WhatsAppRenderError):
        render_interactive(InteractiveKind.TEMPLATE, to="1", name="")


# ---- replay parity (S349) --------------------------------------------------


def test_replay_parity_for_interactive_render() -> None:
    """Two identical render calls must produce byte-equal results."""
    args: dict[str, object] = {
        "to": "123",
        "body": "Pick",
        "buttons": [ReplyButton(id="a", title="A")],
    }
    a = render_interactive(InteractiveKind.BUTTON, **args)  # type: ignore[arg-type]
    b = render_interactive(InteractiveKind.BUTTON, **args)  # type: ignore[arg-type]
    assert a == b

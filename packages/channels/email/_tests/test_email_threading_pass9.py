"""Pass9 email-threading tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from loop_channels_email.threading import (
    EmailHeaders,
    ThreadCorrelator,
    normalise_message_id,
    parse_references,
)


def test_normalise_strips_angles():
    assert normalise_message_id("<abc@x>") == "abc@x"
    assert normalise_message_id("  abc@x  ") == "abc@x"


def test_normalise_rejects_empty():
    with pytest.raises(ValueError):
        normalise_message_id("")
    with pytest.raises(ValueError):
        normalise_message_id("<>")


def test_normalise_rejects_internal_whitespace():
    with pytest.raises(ValueError):
        normalise_message_id("<a b@x>")


def test_parse_references_preserves_order():
    out = parse_references("<root@x> <middle@x> <leaf@x>")
    assert out == ["root@x", "middle@x", "leaf@x"]


def test_parse_references_empty():
    assert parse_references("") == []
    assert parse_references("no-angles") == []


def test_new_thread_when_no_ancestors():
    cor = ThreadCorrelator()
    out = cor.correlate(
        workspace_id=uuid4(),
        headers=EmailHeaders(message_id="<msg-1@x>"),
    )
    assert out.is_new_thread is True


def test_reply_correlates_via_in_reply_to():
    cor = ThreadCorrelator()
    ws = uuid4()
    a = cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<root@x>"))
    b = cor.correlate(
        workspace_id=ws,
        headers=EmailHeaders(message_id="<reply@x>", in_reply_to="<root@x>"),
    )
    assert b.is_new_thread is False
    assert b.conversation_id == a.conversation_id


def test_reply_correlates_via_references_chain():
    cor = ThreadCorrelator()
    ws = uuid4()
    a = cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<root@x>"))
    b = cor.correlate(
        workspace_id=ws,
        headers=EmailHeaders(
            message_id="<deep@x>",
            references=("<root@x>", "<other@x>"),
        ),
    )
    assert b.conversation_id == a.conversation_id


def test_in_reply_to_wins_over_references():
    cor = ThreadCorrelator()
    ws = uuid4()
    a = cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<thread-a@x>"))
    cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<thread-b@x>"))
    out = cor.correlate(
        workspace_id=ws,
        headers=EmailHeaders(
            message_id="<reply@x>",
            in_reply_to="<thread-a@x>",
            references=("<thread-b@x>",),
        ),
    )
    assert out.conversation_id == a.conversation_id


def test_workspace_isolation():
    cor = ThreadCorrelator()
    ws_a = uuid4()
    ws_b = uuid4()
    a = cor.correlate(workspace_id=ws_a, headers=EmailHeaders(message_id="<root@x>"))
    b = cor.correlate(
        workspace_id=ws_b,
        headers=EmailHeaders(message_id="<reply@x>", in_reply_to="<root@x>"),
    )
    assert b.is_new_thread is True
    assert b.conversation_id != a.conversation_id


def test_known_lookup():
    cor = ThreadCorrelator()
    ws = uuid4()
    cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<root@x>"))
    assert cor.known(ws, "<root@x>")
    assert not cor.known(ws, "<unseen@x>")


def test_malformed_reference_skipped_silently():
    cor = ThreadCorrelator()
    ws = uuid4()
    a = cor.correlate(workspace_id=ws, headers=EmailHeaders(message_id="<root@x>"))
    out = cor.correlate(
        workspace_id=ws,
        headers=EmailHeaders(
            message_id="<r@x>",
            references=("<>", "<root@x>"),
        ),
    )
    assert out.conversation_id == a.conversation_id

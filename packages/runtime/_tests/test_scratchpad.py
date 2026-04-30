"""Pass6 SharedScratchpad tests (S406)."""

from __future__ import annotations

import pytest
from loop_runtime.scratchpad import ScratchpadError, SharedScratchpad


def test_isolation_between_siblings() -> None:
    pad = SharedScratchpad()
    pad.open_scope("parent")
    pad.open_scope("childA", parent="parent")
    pad.open_scope("childB", parent="parent")
    pad.set("childA", "secret", "alpha")
    pad.set("childB", "secret", "beta")
    assert pad.get("childA", "secret") == "alpha"
    assert pad.get("childB", "secret") == "beta"


def test_child_sees_parent_writes() -> None:
    pad = SharedScratchpad()
    pad.open_scope("parent")
    pad.open_scope("child", parent="parent")
    pad.set("parent", "topic", "ai")
    assert pad.get("child", "topic") == "ai"


def test_child_cannot_leak_up_to_parent() -> None:
    pad = SharedScratchpad()
    pad.open_scope("parent")
    pad.open_scope("child", parent="parent")
    pad.set("child", "note", "hidden")
    with pytest.raises(ScratchpadError):
        pad.get("parent", "note")


def test_shared_scope_visible_everywhere() -> None:
    pad = SharedScratchpad()
    pad.open_scope("a")
    pad.open_scope("b")
    pad.set_shared("policy", "v1")
    assert pad.get("a", "policy") == "v1"
    assert pad.get("b", "policy") == "v1"


def test_view_merges_scope_chain() -> None:
    pad = SharedScratchpad()
    pad.open_scope("p")
    pad.open_scope("c", parent="p")
    pad.set_shared("a", 1)
    pad.set("p", "b", 2)
    pad.set("c", "c", 3)
    assert dict(pad.view("c")) == {"a": 1, "b": 2, "c": 3}


def test_shared_is_reserved() -> None:
    pad = SharedScratchpad()
    with pytest.raises(ScratchpadError):
        pad.open_scope("shared")


def test_unknown_scope_raises() -> None:
    pad = SharedScratchpad()
    with pytest.raises(ScratchpadError):
        pad.set("missing", "k", 1)
    with pytest.raises(ScratchpadError):
        pad.get("missing", "k")

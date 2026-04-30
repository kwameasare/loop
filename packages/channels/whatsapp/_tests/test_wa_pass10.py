"""Tests for pass10 WhatsApp interactive + media download (S347, S344)."""

# ruff: noqa: S106

from __future__ import annotations

import pytest
from loop_channels_whatsapp.interactive import (
    Button,
    ButtonReplyMessage,
    InteractiveError,
    ListMessage,
    Row,
    Section,
    render_button_reply,
    render_list,
)
from loop_channels_whatsapp.media_download import (
    CachedMedia,
    InMemoryMediaCache,
    WaMediaDownloader,
    WhatsAppMediaError,
)

# --------------------------- interactive ---------------------------


def test_button_reply_renders_basic_shape():
    msg = ButtonReplyMessage(
        body="pick one",
        buttons=(Button(id="a", title="A"), Button(id="b", title="B")),
    )
    out = render_button_reply(to="+1", msg=msg)
    assert out["messaging_product"] == "whatsapp"
    assert out["type"] == "interactive"
    buttons = out["interactive"]["action"]["buttons"]
    assert [b["reply"]["id"] for b in buttons] == ["a", "b"]


def test_button_reply_rejects_too_many():
    with pytest.raises(InteractiveError):
        ButtonReplyMessage(
            body="x",
            buttons=tuple(Button(id=f"b{i}", title=str(i)) for i in range(4)),
        )


def test_button_reply_rejects_dup_ids():
    with pytest.raises(InteractiveError):
        ButtonReplyMessage(
            body="x",
            buttons=(Button(id="a", title="A"), Button(id="a", title="B")),
        )


def test_button_reply_rejects_long_title():
    with pytest.raises(InteractiveError):
        Button(id="i", title="x" * 21)


def test_button_reply_includes_header_footer():
    msg = ButtonReplyMessage(
        body="b",
        buttons=(Button(id="a", title="A"),),
        header="hdr",
        footer="ftr",
    )
    out = render_button_reply(to="+1", msg=msg)
    assert out["interactive"]["header"] == {"type": "text", "text": "hdr"}
    assert out["interactive"]["footer"] == {"text": "ftr"}


def test_list_message_renders_sections():
    msg = ListMessage(
        body="pick",
        button_label="Choose",
        sections=(
            Section(title="Group", rows=(
                Row(id="r1", title="One", description="d1"),
                Row(id="r2", title="Two"),
            )),
        ),
    )
    out = render_list(to="+1", msg=msg)
    sections = out["interactive"]["action"]["sections"]
    assert sections[0]["rows"][0] == {"id": "r1", "title": "One", "description": "d1"}
    assert sections[0]["rows"][1] == {"id": "r2", "title": "Two"}
    assert out["interactive"]["action"]["button"] == "Choose"


def test_list_rejects_more_than_max_rows():
    with pytest.raises(InteractiveError):
        ListMessage(
            body="b",
            button_label="bl",
            sections=(
                Section(title="t", rows=tuple(
                    Row(id=f"r{i}", title=f"t{i}") for i in range(11)
                )),
            ),
        )


def test_list_rejects_dup_row_ids():
    with pytest.raises(InteractiveError):
        ListMessage(
            body="b",
            button_label="bl",
            sections=(
                Section(title="A", rows=(Row(id="x", title="1"),)),
                Section(title="B", rows=(Row(id="x", title="2"),)),
            ),
        )


# --------------------------- media download ---------------------------


class FakeHttp:
    def __init__(self, *, meta: dict, blob: bytes):
        self.meta = meta
        self.blob = blob
        self.json_calls = 0
        self.byte_calls = 0

    async def get_json(self, url, *, headers):
        self.json_calls += 1
        return self.meta

    async def get_bytes(self, url, *, headers):
        self.byte_calls += 1
        return self.blob


@pytest.mark.asyncio
async def test_media_downloader_round_trip_and_cache_hit():
    http = FakeHttp(
        meta={"url": "https://lookaside/abc", "mime_type": "audio/ogg"},
        blob=b"OGG",
    )
    cache = InMemoryMediaCache()
    dl = WaMediaDownloader(http=http, cache=cache)
    out1 = await dl.download(media_id="m1", access_token="tok")
    assert out1.bytes_ == b"OGG" and out1.mime_type == "audio/ogg"
    out2 = await dl.download(media_id="m1", access_token="tok")
    assert out2 is out1 or out2.bytes_ == b"OGG"
    # Cache hit prevents extra HTTP calls.
    assert http.json_calls == 1
    assert http.byte_calls == 1


@pytest.mark.asyncio
async def test_media_downloader_rejects_oversize():
    http = FakeHttp(
        meta={"url": "https://x/", "mime_type": "image/png"},
        blob=b"x" * 2048,
    )
    dl = WaMediaDownloader(
        http=http, cache=InMemoryMediaCache(), max_bytes=1024
    )
    with pytest.raises(WhatsAppMediaError):
        await dl.download(media_id="m", access_token="t")


@pytest.mark.asyncio
async def test_media_downloader_requires_url_and_mime():
    http = FakeHttp(meta={"url": "", "mime_type": "image/png"}, blob=b"")
    dl = WaMediaDownloader(http=http, cache=InMemoryMediaCache())
    with pytest.raises(WhatsAppMediaError):
        await dl.download(media_id="m", access_token="t")

    http2 = FakeHttp(meta={"url": "https://x/", "mime_type": ""}, blob=b"")
    dl2 = WaMediaDownloader(http=http2, cache=InMemoryMediaCache())
    with pytest.raises(WhatsAppMediaError):
        await dl2.download(media_id="m", access_token="t")


@pytest.mark.asyncio
async def test_media_downloader_requires_inputs():
    dl = WaMediaDownloader(http=FakeHttp(meta={}, blob=b""), cache=InMemoryMediaCache())
    with pytest.raises(WhatsAppMediaError):
        await dl.download(media_id="", access_token="t")
    with pytest.raises(WhatsAppMediaError):
        await dl.download(media_id="m", access_token="")


def test_downloader_validates_ctor_args():
    with pytest.raises(ValueError):
        WaMediaDownloader(
            http=FakeHttp(meta={}, blob=b""),
            cache=InMemoryMediaCache(),
            ttl_seconds=5,
        )
    with pytest.raises(ValueError):
        WaMediaDownloader(
            http=FakeHttp(meta={}, blob=b""),
            cache=InMemoryMediaCache(),
            max_bytes=10,
        )


@pytest.mark.asyncio
async def test_in_memory_cache_evicts_oldest():
    cache = InMemoryMediaCache(max_entries=2)
    for i in range(3):
        await cache.put(
            CachedMedia(media_id=f"m{i}", bytes_=b"x", mime_type="t/x", fetched_at_ms=0),
            ttl_seconds=60,
        )
    # m0 was oldest insertion → evicted
    assert await cache.get("m0") is None
    assert await cache.get("m1") is not None
    assert await cache.get("m2") is not None

"""Gateway-call cassettes (S246 / S247).

A *cassette* is a JSONL file containing one ``CassetteEntry`` per line. Each
entry captures (request, response, usage) so a deterministic replay can serve
the same response without hitting the live provider.

The format is intentionally simple and stable so Python tooling, ``jq`` on
the command line, and the studio "diff vs production" UI can all read it:

```
{"request": {...}, "response": "...", "usage": {...}, "recorded_at_ms": 17...}
```

Public surface:

* ``CassetteEntry`` -- pydantic v2 strict frozen model.
* ``CassetteRecorder`` -- captures entries through a request hash key.
* ``CassetteReplayer`` -- looks up the matching entry; raises
  ``CassetteMiss`` when nothing matches.

Both halves use the same ``request_key`` derivation so a recorder can write
a cassette that a replayer plugged into the same code path can serve.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CassetteEntry(BaseModel):
    """One recorded gateway interaction."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    request_key: str = Field(min_length=1)
    request: dict[str, Any] = Field(default_factory=dict)
    response: str
    usage: dict[str, float] = Field(default_factory=dict)
    recorded_at_ms: int = Field(ge=0)


class CassetteMiss(KeyError):  # noqa: N818 - KeyError-shaped lookup miss
    """Raised by `CassetteReplayer.lookup` when no entry matches."""


def request_key(request: dict[str, Any]) -> str:
    """Deterministic hash of a gateway-call request dict.

    Stable across Python runs and platforms: keys are sorted, every value
    is JSON-encoded with ``sort_keys=True``, and a SHA-256 digest is taken.
    Callers are expected to strip transport-only fields (request_id,
    timestamps, retry counters) before hashing.
    """

    blob = json.dumps(request, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def serialise_entry(entry: CassetteEntry) -> str:
    return json.dumps(
        entry.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def parse_entry(line: str) -> CassetteEntry:
    raw = line.strip()
    if not raw:
        raise ValueError("empty cassette line")
    data = json.loads(raw)
    return CassetteEntry.model_validate(data)


class CassetteRecorder:
    """Append-only writer for cassette entries.

    The recorder writes to the underlying buffer eagerly so a crash mid-run
    still leaves a partial-but-valid cassette. JSONL framing means readers
    only need to skip the trailing partial line on recovery.
    """

    def __init__(self, sink: io.TextIOBase) -> None:
        self._sink = sink
        self._count = 0

    @classmethod
    def to_path(cls, path: str | Path) -> CassetteRecorder:
        sink = Path(path).open("a", encoding="utf-8")  # noqa: SIM115 - long-lived recorder owns the handle
        return cls(sink)

    def record(
        self,
        *,
        request: dict[str, Any],
        response: str,
        usage: dict[str, float] | None = None,
        recorded_at_ms: int,
    ) -> CassetteEntry:
        entry = CassetteEntry(
            request_key=request_key(request),
            request=request,
            response=response,
            usage=usage or {},
            recorded_at_ms=recorded_at_ms,
        )
        self._sink.write(serialise_entry(entry) + "\n")
        self._sink.flush()
        self._count += 1
        return entry

    @property
    def count(self) -> int:
        return self._count

    def close(self) -> None:
        self._sink.close()


class CassetteReplayer:
    """Read-only lookup over recorded entries.

    Last-write-wins semantics: if two entries share a ``request_key`` the
    later one shadows the earlier so re-recording a flaky call is safe.
    """

    def __init__(self, entries: Iterable[CassetteEntry]) -> None:
        self._by_key: dict[str, CassetteEntry] = {}
        for e in entries:
            self._by_key[e.request_key] = e

    @classmethod
    def from_path(cls, path: str | Path) -> CassetteReplayer:
        return cls(load_cassette(path))

    def lookup(self, request: dict[str, Any]) -> CassetteEntry:
        key = request_key(request)
        try:
            return self._by_key[key]
        except KeyError as exc:
            raise CassetteMiss(
                f"no cassette entry matches request_key={key[:12]}..."
            ) from exc

    def __contains__(self, request: dict[str, Any]) -> bool:
        return request_key(request) in self._by_key

    def __len__(self) -> int:
        return len(self._by_key)


def load_cassette(path: str | Path) -> Iterator[CassetteEntry]:
    """Yield entries from a cassette file, skipping blank lines."""

    p = Path(path)
    with p.open("r", encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            yield parse_entry(raw)


__all__ = [
    "CassetteEntry",
    "CassetteMiss",
    "CassetteRecorder",
    "CassetteReplayer",
    "load_cassette",
    "parse_entry",
    "request_key",
    "serialise_entry",
]

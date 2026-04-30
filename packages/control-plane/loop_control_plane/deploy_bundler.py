"""Deterministic deploy artifact bundler (S260).

Packs a directory tree into a zip whose bytes are content-addressable: the
same input tree always yields the same SHA-256, regardless of file system
mtimes, traversal order, or the host machine.

Why we care: the deploy controller (`loop_control_plane.deploy`) keys its
caches on artifact hashes, signs releases with cosign, and refuses to
re-promote a version unless the hash matches what was approved. Any
non-determinism here would leak into "phantom" rebuilds and signature
mismatches, both of which we explicitly want to avoid (ADR-024).

Determinism guarantees we enforce:

* file entries are sorted by their relative path (POSIX separators);
* every entry uses the same fixed timestamp (1980-01-01, the zip epoch);
* unix permissions are normalised to ``0o644`` for files and ``0o755``
  for directories;
* compression is ``ZIP_DEFLATED`` with the default level (level=6); we
  never use ``ZIP_STORED`` even for incompressible inputs, because the
  level choice is part of the contract.

The bundler refuses symlinks: they introduce host-dependent behaviour
(both for hashing and for the eventual Docker COPY) that is not worth
the complexity for v0.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# The zip format only encodes timestamps from 1980-01-01 onwards.
_FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class BundlerError(ValueError):
    """Raised when the input tree cannot be bundled deterministically."""


@dataclass(frozen=True)
class BundleResult:
    """Returned from `bundle`. ``data`` is the raw zip bytes."""

    data: bytes
    sha256: str
    entry_count: int


def _iter_files(root: Path, *, exclude: tuple[str, ...]) -> Iterable[Path]:
    excludes = tuple(exclude)
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise BundlerError(
                f"refusing to bundle symlink: {p.relative_to(root)}"
            )
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if any(part in excludes for part in rel.split("/")):
            continue
        yield p


def bundle(
    source: str | Path,
    *,
    exclude: tuple[str, ...] = ("__pycache__", ".git", ".pytest_cache"),
) -> BundleResult:
    """Bundle ``source`` into a deterministic zip blob.

    The exclusion list is deliberately conservative; callers should pass
    extra patterns explicitly rather than relying on us to guess.
    """

    root = Path(source)
    if not root.is_dir():
        raise BundlerError(f"{root}: not a directory")

    buf = io.BytesIO()
    entry_count = 0
    files = list(_iter_files(root, exclude=exclude))
    if not files:
        raise BundlerError(f"{root}: contains no files to bundle")

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(root).as_posix()
            data = path.read_bytes()
            info = zipfile.ZipInfo(filename=rel, date_time=_FIXED_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            # 0o100644 = regular file, mode 0644
            info.external_attr = (0o100644 & 0xFFFF) << 16
            info.create_system = 3  # Unix; constant across platforms
            zf.writestr(info, data)
            entry_count += 1

    payload = buf.getvalue()
    return BundleResult(
        data=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
        entry_count=entry_count,
    )


def bundle_to_path(
    source: str | Path,
    destination: str | Path,
    *,
    exclude: tuple[str, ...] = ("__pycache__", ".git", ".pytest_cache"),
) -> BundleResult:
    """Convenience wrapper that writes the bundle to ``destination``."""

    result = bundle(source, exclude=exclude)
    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(result.data)
    return result


__all__ = ["BundleResult", "BundlerError", "bundle", "bundle_to_path"]

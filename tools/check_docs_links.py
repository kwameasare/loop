"""Validate the docs/ navigation manifest matches the filesystem.

Rules:
1. Every Markdown file under ``docs/`` is referenced from ``docs/index.md``
   exactly once (except ``docs/index.md`` itself).
2. Every link in ``docs/index.md`` resolves to a file that exists.
3. Internal Markdown links (``[..](./foo.md)``) inside docs files resolve
   to a file that exists.

Exit non-zero on any failure with a human-readable diff. Used in CI to
keep the docs site v0 honest while we don't yet have a real generator.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
INDEX = DOCS / "index.md"
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _walk_md_files() -> list[Path]:
    return sorted(p for p in DOCS.rglob("*.md"))


def _links_in(path: Path) -> list[str]:
    return LINK_RE.findall(path.read_text())


def _is_internal(link: str) -> bool:
    if link.startswith(("http://", "https://", "mailto:")):
        return False
    return link.endswith(".md") or ".md#" in link


def _resolve(base: Path, link: str) -> Path:
    target = link.split("#", 1)[0]
    return (base.parent / target).resolve()


def main() -> int:
    failures: list[str] = []

    if not INDEX.exists():
        print(f"ERROR: {INDEX} is missing")
        return 1

    md_files = _walk_md_files()
    expected = {p for p in md_files if p != INDEX}

    index_links = [link for link in _links_in(INDEX) if _is_internal(link)]
    referenced: set[Path] = set()
    for link in index_links:
        target = _resolve(INDEX, link)
        if not target.exists():
            failures.append(f"index.md links to missing file: {link}")
            continue
        referenced.add(target)

    missing_from_index = expected - referenced
    if missing_from_index:
        for p in sorted(missing_from_index):
            failures.append(f"docs/index.md does not reference {p.relative_to(DOCS)}")

    extra = referenced - expected
    for p in sorted(extra):
        failures.append(
            f"docs/index.md references {p.relative_to(DOCS)} which does not exist"
        )

    for md in md_files:
        for link in _links_in(md):
            if not _is_internal(link):
                continue
            target = _resolve(md, link)
            if not target.exists():
                rel = md.relative_to(DOCS)
                failures.append(f"{rel} -> broken link {link}")

    if failures:
        print("docs-links: FAIL")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"docs-links: ok ({len(md_files)} files, {len(index_links)} index links)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

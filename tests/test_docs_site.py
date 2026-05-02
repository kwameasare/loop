"""Validate the docs.loop.example v1 docs site (S659).

Asserts:

* mint.json parses and lists every required page in `navigation`.
* Every page referenced from navigation exists on disk.
* Every internal `(/...)` markdown link in the published `.mdx` resolves
  to a real page.
* Three design-partner sign-offs are committed in PARTNER_REVIEWS.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs" / "site"

REQUIRED_PAGES = (
    "introduction",
    "quickstart",
    "tutorials/build-support-agent",
    "tutorials/connect-channels",
    "tutorials/eval-and-deploy",
)


def _load_mint() -> dict:
    return json.loads((DOCS / "mint.json").read_text(encoding="utf-8"))


def test_mint_json_parses() -> None:
    cfg = _load_mint()
    assert cfg["name"] == "Loop"
    assert "navigation" in cfg and cfg["navigation"]


def test_navigation_lists_every_required_page() -> None:
    cfg = _load_mint()
    listed: set[str] = set()
    for group in cfg["navigation"]:
        for page in group["pages"]:
            listed.add(page)
    for required in REQUIRED_PAGES:
        assert required in listed, f"navigation missing {required}"


@pytest.mark.parametrize("slug", REQUIRED_PAGES)
def test_required_page_file_exists(slug: str) -> None:
    path = DOCS / f"{slug}.mdx"
    assert path.exists(), f"missing {path}"
    assert path.stat().st_size > 200, f"{path} is suspiciously short"


def test_every_navigation_page_exists_on_disk() -> None:
    cfg = _load_mint()
    missing: list[str] = []
    for group in cfg["navigation"]:
        for slug in group["pages"]:
            path = DOCS / f"{slug}.mdx"
            if not path.exists():
                missing.append(slug)
    # Concept pages live in the existing docs/concepts tree; pages that
    # aren't part of the v1 site bundle are allowed to live elsewhere as
    # long as they exist somewhere under docs/. Resolve them with a
    # secondary lookup before failing.
    for slug in list(missing):
        if slug.startswith("concepts/"):
            alt = REPO_ROOT / "docs" / f"{slug}.md"
            if alt.exists():
                missing.remove(slug)
    assert missing == [], f"navigation references missing pages: {missing}"


_LINK_RE = re.compile(r"\[[^\]]+\]\((/[^)#?]*)")


def test_internal_links_resolve() -> None:
    """Every (/...) link in the v1 mdx pages must point at a real page."""
    broken: list[str] = []
    for mdx in DOCS.rglob("*.mdx"):
        for match in _LINK_RE.finditer(mdx.read_text(encoding="utf-8")):
            target = match.group(1).lstrip("/")
            if not target:
                continue
            # Skip API/changelog anchors — those are generated post-build.
            if target.startswith(("api", "changelog")):
                continue
            candidates = [
                DOCS / f"{target}.mdx",
                DOCS / target / "index.mdx",
                REPO_ROOT / "docs" / f"{target}.md",
            ]
            if not any(c.exists() for c in candidates):
                broken.append(f"{mdx.name} -> /{target}")
    assert broken == [], f"broken internal links: {broken}"


def test_three_design_partner_signoffs() -> None:
    body = (DOCS / "PARTNER_REVIEWS.md").read_text(encoding="utf-8")
    # Each partner row in the table has the verdict column "Approved".
    assert body.count("Approved") >= 3
    for partner in ("Acme Logistics", "Northwind Commerce", "Helios Insurance"):
        assert partner in body, f"missing signoff from {partner}"
    # AC explicitly says "checked by 3 design partners".
    assert "3 design partners" in body or "three design partners" in body.lower()

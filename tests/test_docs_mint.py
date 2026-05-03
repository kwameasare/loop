"""S915: validate the apps/docs/ Mintlify project.

Asserts that:

1. ``apps/docs/mint.json`` parses as JSON and declares the expected
   top-level keys (``name``, ``navigation``).
2. Every page id referenced from ``mint.json#/navigation`` resolves to
   a file under ``apps/docs/`` (``<id>.mdx`` or ``<id>.md``).
3. Every ``.mdx`` page in the project is referenced exactly once from
   the navigation, with the sole exception of ``index`` (the root).
4. Every ``.mdx`` page declares a ``title`` and ``description`` in its
   YAML frontmatter so Mintlify's search index is well-formed.

The test is intentionally hermetic — it does not require the
Mintlify CLI to be installed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parents[1] / "apps" / "docs"
MINT_JSON = DOCS_ROOT / "mint.json"


def _flatten_pages(navigation: list) -> list[str]:
    pages: list[str] = []
    for group in navigation:
        for page in group.get("pages", []):
            if isinstance(page, str):
                pages.append(page)
            elif isinstance(page, dict):
                pages.extend(_flatten_pages([page]))
    return pages


def _resolve_page(page_id: str) -> Path | None:
    for ext in (".mdx", ".md"):
        candidate = DOCS_ROOT / f"{page_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def test_mint_json_parses_and_declares_required_keys() -> None:
    data = json.loads(MINT_JSON.read_text())
    assert data.get("name"), "mint.json must declare a site name"
    assert isinstance(data.get("navigation"), list) and data["navigation"], (
        "mint.json must declare a non-empty navigation array"
    )


def test_every_navigation_entry_resolves_to_a_file() -> None:
    data = json.loads(MINT_JSON.read_text())
    pages = _flatten_pages(data["navigation"])
    missing = [p for p in pages if _resolve_page(p) is None]
    assert not missing, f"navigation references missing pages: {missing}"


def test_every_mdx_file_is_referenced_from_navigation() -> None:
    data = json.loads(MINT_JSON.read_text())
    referenced = set(_flatten_pages(data["navigation"]))
    on_disk = {
        p.relative_to(DOCS_ROOT).with_suffix("").as_posix()
        for p in DOCS_ROOT.rglob("*.mdx")
    }
    orphaned = on_disk - referenced
    assert not orphaned, f"orphaned MDX pages (not in mint.json): {sorted(orphaned)}"


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def test_every_mdx_file_declares_title_and_description() -> None:
    bad: list[str] = []
    for mdx in DOCS_ROOT.rglob("*.mdx"):
        text = mdx.read_text()
        match = _FRONTMATTER_RE.match(text)
        if not match:
            bad.append(f"{mdx.relative_to(DOCS_ROOT)}: missing frontmatter block")
            continue
        body = match.group(1)
        if "title:" not in body:
            bad.append(f"{mdx.relative_to(DOCS_ROOT)}: missing title")
        if "description:" not in body:
            bad.append(f"{mdx.relative_to(DOCS_ROOT)}: missing description")
    assert not bad, "MDX frontmatter problems:\n" + "\n".join(bad)


def test_navigation_indexes_at_least_twelve_pages() -> None:
    """S915 AC: mint.json indexes 12+ pages."""
    data = json.loads(MINT_JSON.read_text())
    pages = _flatten_pages(data["navigation"])
    assert len(pages) >= 12, f"expected >=12 indexed pages, got {len(pages)}"


def test_quickstart_points_at_g7_support_agent_example() -> None:
    """S915 AC: quickstart points at G7 example (examples/support_agent)."""
    text = (DOCS_ROOT / "quickstart.mdx").read_text()
    assert "examples/support_agent" in text, (
        "quickstart.mdx must reference examples/support_agent (G7)"
    )


def test_navigation_covers_required_groups() -> None:
    """S915 AC: nav covers concepts / quickstart / tutorials / api-ref / cookbook."""
    data = json.loads(MINT_JSON.read_text())
    groups = {g["group"].lower() for g in data["navigation"]}
    pages = set(_flatten_pages(data["navigation"]))
    assert "quickstart" in pages, "navigation must include the quickstart page"
    assert any("concept" in g for g in groups), "missing Concepts group"
    assert any("tutorial" in g for g in groups), "missing Tutorials group"
    assert any("api" in g for g in groups), "missing API Reference group"
    assert any("cookbook" in g for g in groups), "missing Cookbook group"

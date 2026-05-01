"""S674 data-room artifact checks."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOM = ROOT / "loop_implementation" / "operations" / "data-room"
DECK = DATA_ROOM / "01_narrative_deck_v2.pptx"
MODEL = DATA_ROOM / "40_financials_model_v3.xlsx"
README = DATA_ROOM / "README.md"
SERIES_A = ROOT / "loop_implementation" / "operations" / "SERIES_A.md"
SHARE_URL = "https://github.com/kwameasare/loop/tree/main/loop_implementation/operations/data-room"


def _zip_text(path: Path) -> str:
    with ZipFile(path) as archive:
        chunks: list[str] = []
        for name in archive.namelist():
            if name.endswith(".xml"):
                chunks.append(archive.read(name).decode("utf-8", errors="ignore"))
    return "\n".join(chunks)


def test_data_room_readme_exposes_shareable_link_and_artifacts() -> None:
    readme = README.read_text()
    series = SERIES_A.read_text()
    assert SHARE_URL in readme
    assert SHARE_URL in series
    assert "01_narrative_deck_v2.pptx" in readme
    assert "40_financials_model_v3.xlsx" in readme
    assert "Checks` tab is all `PASS`" in readme


def test_narrative_deck_is_committed_pptx_with_expected_story() -> None:
    assert DECK.stat().st_size > 20_000
    with ZipFile(DECK) as archive:
        slides = [name for name in archive.namelist() if name.startswith("ppt/slides/slide")]
    text = _zip_text(DECK)
    assert len([name for name in slides if name.endswith(".xml")]) == 6
    assert "agent operations plane" in text
    assert "$18M" in text
    assert "data-room/40_financials_model_v3.xlsx" in text


def test_financial_model_is_committed_xlsx_with_formulas_and_checks() -> None:
    assert MODEL.stat().st_size > 10_000
    with ZipFile(MODEL) as archive:
        names = set(archive.namelist())
        assert "xl/workbook.xml" in names
        assert any(name.startswith("xl/worksheets/sheet") for name in names)
    text = _zip_text(MODEL)
    assert "Loop Series A financial model v3" in text
    assert "Operating Model" in text
    assert "Assumptions" in text
    assert "SUM(Summary!B14:B17)" in text
    assert "PASS" in text

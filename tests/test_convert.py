"""Tests for src/convert.py.

Real fixtures live in tests/fixtures/ — do NOT mock the filesystem.
Add cases as the converter grows: nav-stripping, title extraction, verse anchors, encoding edge cases.
"""

from __future__ import annotations

from pathlib import Path

from src.convert import convert_html

FIXTURES = Path(__file__).parent / "fixtures"


def _convert(name: str):
    return convert_html((FIXTURES / name).read_text(encoding="utf-8"))


def test_strips_nav_blocks() -> None:
    result = _convert("kjv_gen001.htm")

    # Top nav: the "Polyglot / Sep / Tan / Vul" link row sits above the first <HR>.
    assert "Polyglot" not in result.body
    assert "Genesis Index" not in result.body
    # Bottom nav: the "Next: Genesis Chapter 2" link sits below the last <HR>.
    assert "Next: Genesis Chapter 2" not in result.body

    # Body text and verse numbers must survive.
    assert "In the beginning God created" in result.body
    assert result.body.lstrip().startswith("King James Version: Genesis Chapter 1")
    assert "1 In the beginning" in result.body
    assert "31 And God saw every thing" in result.body


def test_preserves_paragraph_breaks() -> None:
    result = _convert("kjv_gen001.htm")

    # Each verse is its own paragraph; blank lines separate them.
    assert "\n\n1 In the beginning" in "\n" + result.body
    assert "earth.\n\n2 And the earth was without form" in result.body
    # No triple-newlines (would mean we lost a paragraph or doubled a break).
    assert "\n\n\n" not in result.body


def test_extracts_title() -> None:
    assert _convert("kjv_gen001.htm").title == (
        "King James Version: Genesis: Genesis Chapter 1"
    )
    assert _convert("kjv_index.htm").title == "King James Version Index"
    assert _convert("site_about.htm").title == "About Sacred-texts.com"

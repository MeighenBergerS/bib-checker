"""Tests for bib_checker.parser."""

from pathlib import Path

import pytest

from bib_checker.parser import parse_bib_file

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_BIB = FIXTURES / "sample.bib"


def test_parse_returns_correct_count():
    entries = parse_bib_file(SAMPLE_BIB)
    assert len(entries) == 4


def test_parse_article_key_and_type():
    entries = parse_bib_file(SAMPLE_BIB)
    spolyar = next(e for e in entries if e.key == "Spolyar:2007qv")
    assert spolyar.entry_type == "article"


def test_parse_fields_extracted():
    entries = parse_bib_file(SAMPLE_BIB)
    spolyar = next(e for e in entries if e.key == "Spolyar:2007qv")
    assert spolyar.doi == "10.1103/PhysRevLett.100.051101"
    assert spolyar.eprint == "0705.0521"
    assert spolyar.year == "2008"


def test_parse_authors_split():
    entries = parse_bib_file(SAMPLE_BIB)
    spolyar = next(e for e in entries if e.key == "Spolyar:2007qv")
    assert len(spolyar.authors) == 3
    assert "Spolyar, Douglas" in spolyar.authors[0] or "Douglas" in spolyar.authors[0]


def test_parse_preprint_type():
    entries = parse_bib_file(SAMPLE_BIB)
    acevedo = next(e for e in entries if e.key == "Acevedo:2025rqu")
    assert acevedo.entry_type == "preprint"


def test_parse_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        parse_bib_file("/nonexistent/path/file.bib")


def test_parse_title_braces_stripped():
    entries = parse_bib_file(SAMPLE_BIB)
    spolyar = next(e for e in entries if e.key == "Spolyar:2007qv")
    # bibtexparser strips outer braces from title
    assert not spolyar.title.startswith("{")

"""Tests for bib_checker.parser."""

from pathlib import Path

import pytest

from bib_checker.parser import parse_bib_file, write_reformatted_bib

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


# ---------------------------------------------------------------------------
# write_reformatted_bib
# ---------------------------------------------------------------------------

_TWO_ENTRY_BIB = """\
@article{Good:2000ab,
    author = "Author, A",
    title = "{Good paper}",
    year = "2000"
}

@article{Bad:2001cd,
    author = "Author, B",
    title = "{Bad paper}",
    year = "2001"
}
"""


def test_write_reformatted_bib_places_flagged_at_end(tmp_path):
    src = tmp_path / "src.bib"
    src.write_text(_TWO_ENTRY_BIB)
    out = tmp_path / "out.bib"
    n_ok, n_bad = write_reformatted_bib(src, {"Bad:2001cd"}, out)
    assert n_ok == 1
    assert n_bad == 1
    content = out.read_text()
    good_pos = content.find("Good:2000ab")
    bad_pos = content.find("Bad:2001cd")
    assert good_pos < bad_pos


def test_write_reformatted_bib_separator_present(tmp_path):
    src = tmp_path / "src.bib"
    src.write_text(_TWO_ENTRY_BIB)
    out = tmp_path / "out.bib"
    write_reformatted_bib(src, {"Bad:2001cd"}, out)
    assert "need validation" in out.read_text()


def test_write_reformatted_bib_no_flagged_no_separator(tmp_path):
    src = tmp_path / "src.bib"
    src.write_text(_TWO_ENTRY_BIB)
    out = tmp_path / "out.bib"
    n_ok, n_bad = write_reformatted_bib(src, set(), out)
    assert n_bad == 0
    assert "need validation" not in out.read_text()


def test_write_reformatted_bib_missing_source_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        write_reformatted_bib(tmp_path / "nonexistent.bib", set(), tmp_path / "out.bib")

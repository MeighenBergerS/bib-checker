"""Tests for bib_checker.fixer."""

from __future__ import annotations

from pathlib import Path

import pytest

from bib_checker.fixer import DEFAULT_FIX_FIELDS, _canonical_values, apply_fixes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BIB = """\
@article{Spolyar:2007qv,
    author = "Spolyar, Douglas",
    title = "{Dark matter and the first stars}",
    doi = "10.1103/PhysRevLett.100.051101",
    eprint = "0705.0521",
    year = "2009"
}

@article{FakeKey:9999xx,
    author = "Nobody, Alice",
    title = "{Does not exist}",
    year = "1900"
}
"""

_INSPIRE_RECORD = {
    "id": "12345",
    "metadata": {
        "texkeys": ["Spolyar:2007qv"],
        "titles": [{"title": "Dark matter and the first stars"}],
        "dois": [{"value": "10.1103/PhysRevLett.100.051101"}],
        "arxiv_eprints": [{"value": "0705.0521"}],
        "publication_info": [{"year": 2008}],
        "authors": [{"full_name": "Spolyar, Douglas"}],
    },
}


def _write_bib(tmp_path: Path, content: str = _BIB) -> Path:
    p = tmp_path / "paper.bib"
    p.write_text(content)
    return p


def _mismatch(tmp_path: Path, fields: list[str] | None = None) -> list[dict]:
    return [
        {
            "key": "Spolyar:2007qv",
            "status": "mismatch",
            "mismatches": [{"field": "year", "local": "2009", "remote": "2008"}],
            "local_entry": {"key": "Spolyar:2007qv", "type": "article", "year": "2009"},
            "inspire_record": _INSPIRE_RECORD,
        }
    ]


def _missing() -> list[dict]:
    return [
        {
            "key": "FakeKey:9999xx",
            "status": "missing",
            "mismatches": [],
            "local_entry": {"key": "FakeKey:9999xx", "type": "article", "year": "1900"},
            "inspire_record": None,
        }
    ]


# ---------------------------------------------------------------------------
# _canonical_values
# ---------------------------------------------------------------------------


def test_canonical_values_extracts_year():
    result = {"inspire_record": _INSPIRE_RECORD}
    vals = _canonical_values(result, ["year"])
    assert vals["year"] == "2008"


def test_canonical_values_extracts_doi():
    result = {"inspire_record": _INSPIRE_RECORD}
    vals = _canonical_values(result, ["doi"])
    assert vals["doi"] == "10.1103/PhysRevLett.100.051101"


def test_canonical_values_missing_record_returns_empty():
    assert _canonical_values({"inspire_record": None}, ["doi", "year"]) == {}


def test_canonical_values_unknown_field_ignored():
    result = {"inspire_record": _INSPIRE_RECORD}
    vals = _canonical_values(result, ["unknown_field"])
    assert vals == {}


def test_default_fix_fields():
    assert set(DEFAULT_FIX_FIELDS) == {"doi", "eprint", "year", "title"}


# ---------------------------------------------------------------------------
# apply_fixes — happy path
# ---------------------------------------------------------------------------


def test_apply_fixes_patches_year(tmp_path):
    bib = _write_bib(tmp_path)
    applied, _ = apply_fixes(bib, _mismatch(tmp_path), output_path=tmp_path / "out.bib")
    assert any(c["field"] == "year" and c["new"] == "2008" for c in applied)


def test_apply_fixes_returns_old_and_new_values(tmp_path):
    bib = _write_bib(tmp_path)
    applied, _ = apply_fixes(bib, _mismatch(tmp_path), output_path=tmp_path / "out.bib")
    year_change = next(c for c in applied if c["field"] == "year")
    assert year_change["old"] == "2009"
    assert year_change["new"] == "2008"


def test_apply_fixes_output_file_written(tmp_path):
    bib = _write_bib(tmp_path)
    out = tmp_path / "out.bib"
    apply_fixes(bib, _mismatch(tmp_path), output_path=out)
    assert out.exists()


# ---------------------------------------------------------------------------
# apply_fixes — dry run
# ---------------------------------------------------------------------------


def test_apply_fixes_dry_run_returns_changes(tmp_path):
    bib = _write_bib(tmp_path)
    out = tmp_path / "out.bib"
    applied, _ = apply_fixes(bib, _mismatch(tmp_path), output_path=out, dry_run=True)
    assert len(applied) > 0


def test_apply_fixes_dry_run_writes_nothing(tmp_path):
    bib = _write_bib(tmp_path)
    out = tmp_path / "out.bib"
    apply_fixes(bib, _mismatch(tmp_path), output_path=out, dry_run=True)
    assert not out.exists()


# ---------------------------------------------------------------------------
# apply_fixes — missing entries
# ---------------------------------------------------------------------------


def test_apply_fixes_missing_not_patched(tmp_path):
    bib = _write_bib(tmp_path)
    applied, _ = apply_fixes(bib, _missing(), output_path=tmp_path / "out.bib")
    assert applied == []


def test_apply_fixes_missing_in_still_flagged(tmp_path):
    bib = _write_bib(tmp_path)
    _, still_flagged = apply_fixes(bib, _missing(), output_path=tmp_path / "out.bib")
    assert "FakeKey:9999xx" in still_flagged


# ---------------------------------------------------------------------------
# apply_fixes — field filtering
# ---------------------------------------------------------------------------


def test_apply_fixes_field_filtering_year_only(tmp_path):
    bib = _write_bib(tmp_path)
    results = [
        {
            "key": "Spolyar:2007qv",
            "status": "mismatch",
            "mismatches": [],
            "local_entry": {"key": "Spolyar:2007qv", "type": "article", "year": "2009"},
            "inspire_record": {
                **_INSPIRE_RECORD,
                "titles": [{"title": "A completely different title"}],
            },
        }
    ]
    applied, _ = apply_fixes(bib, results, output_path=tmp_path / "out.bib", fields=["year"])
    field_names = [c["field"] for c in applied]
    assert "year" in field_names
    assert "title" not in field_names


# ---------------------------------------------------------------------------
# apply_fixes — default output path
# ---------------------------------------------------------------------------


def test_apply_fixes_default_output_is_fixed_bib(tmp_path):
    bib = _write_bib(tmp_path)
    apply_fixes(bib, _missing())
    expected = bib.parent / "paper_fixed.bib"
    assert expected.exists()
    expected.unlink()  # clean up


# ---------------------------------------------------------------------------
# apply_fixes — separator layout
# ---------------------------------------------------------------------------


def test_apply_fixes_flagged_entries_after_separator(tmp_path):
    bib = _write_bib(tmp_path)
    out = tmp_path / "out.bib"
    apply_fixes(bib, _missing(), output_path=out)
    content = out.read_text()
    sep_pos = content.find("need validation")
    fake_pos = content.find("FakeKey:9999xx")
    assert sep_pos != -1
    assert fake_pos != -1
    assert sep_pos < fake_pos


def test_apply_fixes_no_separator_when_nothing_flagged(tmp_path):
    bib = _write_bib(tmp_path)
    # A result dict with a mismatch that has a clean record — should be fully fixed.
    results = [
        {
            "key": "Spolyar:2007qv",
            "status": "mismatch",
            "mismatches": [],
            "local_entry": {"key": "Spolyar:2007qv", "type": "article", "year": "2009"},
            "inspire_record": _INSPIRE_RECORD,
        }
    ]
    out = tmp_path / "out.bib"
    _, still_flagged = apply_fixes(bib, results, output_path=out)
    assert "Spolyar:2007qv" not in still_flagged


# ---------------------------------------------------------------------------
# apply_fixes — error handling
# ---------------------------------------------------------------------------


def test_apply_fixes_missing_bib_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        apply_fixes(tmp_path / "nonexistent.bib", [])

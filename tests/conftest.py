"""Shared pytest fixtures for bib-checker tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from bib_checker.models import BibEntry, CheckResult, FieldMismatch


# ---------------------------------------------------------------------------
# Bib file helpers
# ---------------------------------------------------------------------------

SIMPLE_BIB_CONTENT = """\
@article{Spolyar:2007qv,
    author = "Spolyar, Douglas and Freese, Katherine and Gondolo, Paolo",
    title = "{Dark matter and the first stars: a new phase of stellar evolution}",
    eprint = "0705.0521",
    archivePrefix = "arXiv",
    doi = "10.1103/PhysRevLett.100.051101",
    journal = "Phys. Rev. Lett.",
    volume = "100",
    pages = "051101",
    year = "2008"
}

@article{FakeKey:9999xx,
    author = "Nobody, Alice",
    title = "{This entry does not exist anywhere}",
    year = "1900"
}
"""


@pytest.fixture
def simple_bib(tmp_path: Path) -> Path:
    """A .bib file with one valid and one fake entry."""
    p = tmp_path / "paper.bib"
    p.write_text(SIMPLE_BIB_CONTENT)
    return p


# ---------------------------------------------------------------------------
# results.json dict fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mismatch_result_dict() -> dict:
    """A results.json entry for a mismatch (wrong year)."""
    return {
        "key": "Spolyar:2007qv",
        "status": "mismatch",
        "nonstandard_key": False,
        "mismatches": [{"field": "year", "local": "2009", "remote": "2008"}],
        "local_entry": {
            "key": "Spolyar:2007qv",
            "type": "article",
            "doi": "10.1103/PhysRevLett.100.051101",
            "eprint": "0705.0521",
            "year": "2009",
            "title": "Dark matter and the first stars: a new phase of stellar evolution",
        },
        "inspire_record": {
            "id": "12345",
            "metadata": {
                "texkeys": ["Spolyar:2007qv"],
                "titles": [{"title": "Dark matter and the first stars: a new phase of stellar evolution"}],
                "dois": [{"value": "10.1103/PhysRevLett.100.051101"}],
                "arxiv_eprints": [{"value": "0705.0521"}],
                "publication_info": [{"year": 2008}],
                "authors": [{"full_name": "Spolyar, Douglas"}],
            },
        },
        "ads_record": None,
    }


@pytest.fixture
def missing_result_dict() -> dict:
    """A results.json entry for a missing entry."""
    return {
        "key": "FakeKey:9999xx",
        "status": "missing",
        "nonstandard_key": True,
        "mismatches": [],
        "local_entry": {
            "key": "FakeKey:9999xx",
            "type": "article",
            "title": "This entry does not exist anywhere",
            "year": "1900",
        },
        "inspire_record": None,
        "ads_record": None,
    }


# ---------------------------------------------------------------------------
# Model fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ok_check_result() -> CheckResult:
    return CheckResult(key="Spolyar:2007qv", status="ok")


@pytest.fixture
def missing_check_result() -> CheckResult:
    return CheckResult(
        key="FakeKey:9999xx",
        status="missing",
        nonstandard_key=True,
        local_entry={"title": "Does not exist", "year": "1900"},
    )


@pytest.fixture
def mismatch_check_result() -> CheckResult:
    return CheckResult(
        key="Spolyar:2007qv",
        status="mismatch",
        mismatches=[FieldMismatch("year", "2009", "2008")],
    )


@pytest.fixture
def sample_bib_entry() -> BibEntry:
    return BibEntry(
        key="Spolyar:2007qv",
        entry_type="article",
        fields={
            "doi": "10.1103/PhysRevLett.100.051101",
            "eprint": "0705.0521",
            "year": "2008",
            "title": "Dark matter and the first stars",
            "author": "Spolyar, Douglas and Freese, Katherine",
        },
    )

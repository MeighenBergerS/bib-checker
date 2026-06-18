"""Tests for bib_checker.searcher (network calls mocked with responses)."""

import json
from pathlib import Path

import responses as rsps_lib

from bib_checker.inspire import InspireClient
from bib_checker.searcher import _build_queries, _first_surname, suggest_replacements

_BASE = "https://inspirehep.net/api/literature"


# ---------------------------------------------------------------------------
# Unit tests — no I/O, no network
# ---------------------------------------------------------------------------


def test_first_surname_last_first_format():
    assert _first_surname("Spolyar, Douglas and Freese, Katherine") == "Spolyar"


def test_first_surname_first_last_format():
    assert _first_surname("Douglas Spolyar and Katherine Freese") == "Spolyar"


def test_build_queries_with_all_fields():
    entry = {
        "eprint": "0705.0521",
        "doi": "10.1103/PhysRevLett.100.051101",
        "author": "Spolyar, Douglas and Freese, Katherine",
        "year": "2008",
    }
    queries = _build_queries(entry)
    assert queries[0] == "arxiv:0705.0521"
    assert any("doi:" in q for q in queries)
    assert any("Spolyar" in q for q in queries)


def test_build_queries_empty_entry_returns_empty():
    queries = _build_queries({})
    assert queries == []


def test_build_queries_eprint_only():
    queries = _build_queries({"eprint": "1234.5678"})
    assert queries == ["arxiv:1234.5678"]


# ---------------------------------------------------------------------------
# Integration-style tests with mocked network
# ---------------------------------------------------------------------------


def _make_results_file(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "results.json"
    p.write_text(json.dumps(entries))
    return p


def _make_hit(texkey: str, title: str, eprint: str) -> dict:
    return {
        "id": "99999",
        "metadata": {
            "texkeys": [texkey],
            "titles": [{"title": title}],
            "dois": [{"value": "10.1/test"}],
            "arxiv_eprints": [{"value": eprint}],
            "publication_info": [{"year": 2008}],
            "authors": [{"full_name": "Test, Author"}],
        },
    }


@rsps_lib.activate
def test_suggest_uses_eprint_first(tmp_path):
    result = {
        "key": "Spolyar:2007qv",
        "status": "missing",
        "local_entry": {
            "eprint": "0705.0521",
            "doi": "",
            "author": "Spolyar, Douglas",
            "year": "2008",
        },
        "mismatches": [],
    }
    results_file = _make_results_file(tmp_path, [result])

    hit = _make_hit("Spolyar:2007qv", "Dark matter and the first stars", "0705.0521")
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    assert len(suggestions) == 1
    assert suggestions[0].texkey == "Spolyar:2007qv"
    assert suggestions[0].for_key == "Spolyar:2007qv"


@rsps_lib.activate
def test_suggest_skips_ok_entries(tmp_path):
    results = [
        {"key": "Good:2000ab", "status": "ok", "local_entry": {}, "mismatches": []},
        {
            "key": "Missing:9999xx",
            "status": "missing",
            "local_entry": {
                "eprint": "9999.9999",
                "doi": "",
                "author": "Nobody, A",
                "year": "1900",
            },
            "mismatches": [],
        },
    ]
    results_file = _make_results_file(tmp_path, results)

    hit = _make_hit("SomeKey:2000ab", "Found paper", "9999.9999")
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    # Only one entry was actionable, so only one set of suggestions.
    assert all(s.for_key == "Missing:9999xx" for s in suggestions)


@rsps_lib.activate
def test_suggest_no_hits_returns_empty(tmp_path):
    result = {
        "key": "FakeKey:0000ab",
        "status": "missing",
        "local_entry": {"eprint": "0000.0000", "doi": "", "author": "", "year": ""},
        "mismatches": [],
    }
    results_file = _make_results_file(tmp_path, [result])

    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": []}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    assert suggestions == []


# ---------------------------------------------------------------------------
# Query priority — doi fallback when no eprint
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_suggest_falls_back_to_doi_when_no_eprint(tmp_path):
    result = {
        "key": "Test:2000ab",
        "status": "missing",
        "local_entry": {
            "eprint": "",
            "doi": "10.1/test",
            "author": "Test, Author",
            "year": "2000",
        },
        "mismatches": [],
    }
    results_file = _make_results_file(tmp_path, [result])

    hit = _make_hit("Test:2000ab", "Found via DOI", "0001.0001")
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    assert len(suggestions) == 1
    # The query used the doi: path — verify a suggestion was returned.
    assert suggestions[0].for_key == "Test:2000ab"


# ---------------------------------------------------------------------------
# Query priority — author+year fallback
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_suggest_falls_back_to_author_year(tmp_path):
    result = {
        "key": "Test:2000ab",
        "status": "missing",
        "local_entry": {
            "eprint": "",
            "doi": "",
            "author": "Smith, John",
            "year": "2000",
        },
        "mismatches": [],
    }
    results_file = _make_results_file(tmp_path, [result])

    hit = _make_hit("Smith:2000ab", "Found via author+year", "0001.0001")
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    assert len(suggestions) == 1
    assert suggestions[0].for_key == "Test:2000ab"


# ---------------------------------------------------------------------------
# Multiple suggestions capped at 5
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_suggest_returns_all_hits_from_api(tmp_path):
    """API is called with size=5; whatever the API returns is passed through."""
    result = {
        "key": "Test:2000ab",
        "status": "missing",
        "local_entry": {"eprint": "0001.0001", "doi": "", "author": "Test, A", "year": "2000"},
        "mismatches": [],
    }
    results_file = _make_results_file(tmp_path, [result])

    hits = [_make_hit(f"Key:200{i}ab", f"Paper {i}", f"000{i}.0001") for i in range(5)]
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": hits}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    suggestions = suggest_replacements(results_file, client=client)

    assert len(suggestions) == 5


# ---------------------------------------------------------------------------
# _build_queries — edge cases
# ---------------------------------------------------------------------------


def test_build_queries_doi_only():
    queries = _build_queries({"doi": "10.1/test"})
    assert any("doi:" in q for q in queries)


def test_build_queries_author_year_fallback():
    queries = _build_queries({"author": "Smith, John", "year": "2000"})
    assert any("Smith" in q for q in queries)
    assert any("2000" in q for q in queries)

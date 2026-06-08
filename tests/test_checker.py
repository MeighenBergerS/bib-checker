"""Tests for bib_checker.checker (all network calls mocked with responses)."""

import responses as rsps_lib

from bib_checker.checker import check_entries
from bib_checker.inspire import InspireClient
from bib_checker.models import BibEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE = "https://inspirehep.net/api/literature"


def _inspire_hit(texkey: str, doi: str, eprint: str, year: int, title: str) -> dict:
    return {
        "id": "12345",
        "metadata": {
            "texkeys": [texkey],
            "titles": [{"title": title}],
            "dois": [{"value": doi}],
            "arxiv_eprints": [{"value": eprint}],
            "publication_info": [{"year": year}],
            "authors": [{"full_name": "Spolyar, Douglas"}],
        },
    }


def _make_entry(
    key: str,
    doi: str = "",
    eprint: str = "",
    year: str = "",
    title: str = "",
) -> BibEntry:
    return BibEntry(
        key=key,
        entry_type="article",
        fields={
            "doi": doi,
            "eprint": eprint,
            "year": year,
            "title": title,
            "author": "Spolyar, Douglas and Freese, Katherine",
        },
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@rsps_lib.activate
def test_entry_ok_when_fields_match():
    entry = _make_entry(
        "Spolyar:2007qv",
        doi="10.1103/PhysRevLett.100.051101",
        eprint="0705.0521",
        year="2008",
        title="Dark matter and the first stars",
    )
    hit = _inspire_hit(
        "Spolyar:2007qv",
        doi="10.1103/PhysRevLett.100.051101",
        eprint="0705.0521",
        year=2008,
        title="Dark matter and the first stars",
    )
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = check_entries([entry], client=client)

    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].mismatches == []


@rsps_lib.activate
def test_entry_missing_when_no_hits():
    entry = _make_entry("FakeKey:9999xx", doi="", eprint="", year="1900")
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": []}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = check_entries([entry], client=client)

    assert results[0].status == "missing"


@rsps_lib.activate
def test_entry_mismatch_on_wrong_year():
    entry = _make_entry(
        "Spolyar:2007qv",
        doi="10.1103/PhysRevLett.100.051101",
        eprint="0705.0521",
        year="2009",  # wrong year
        title="Dark matter and the first stars",
    )
    hit = _inspire_hit(
        "Spolyar:2007qv",
        doi="10.1103/PhysRevLett.100.051101",
        eprint="0705.0521",
        year=2008,  # correct year from inspire
        title="Dark matter and the first stars",
    )
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = check_entries([entry], client=client)

    assert results[0].status == "mismatch"
    mismatch_fields = [m.field_name for m in results[0].mismatches]
    assert "year" in mismatch_fields


@rsps_lib.activate
def test_entry_mismatch_on_wrong_doi():
    entry = _make_entry(
        "Spolyar:2007qv",
        doi="10.1103/WRONG.DOI",
        eprint="0705.0521",
        year="2008",
        title="Dark matter and the first stars",
    )
    hit = _inspire_hit(
        "Spolyar:2007qv",
        doi="10.1103/PhysRevLett.100.051101",
        eprint="0705.0521",
        year=2008,
        title="Dark matter and the first stars",
    )
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = check_entries([entry], client=client)

    assert results[0].status == "mismatch"
    mismatch_fields = [m.field_name for m in results[0].mismatches]
    assert "doi" in mismatch_fields


@rsps_lib.activate
def test_multiple_entries_mixed_results():
    entries = [
        _make_entry("Good:2000ab", doi="10.1/good", eprint="0001.0001", year="2000"),
        _make_entry("Missing:9999xx"),
    ]

    good_hit = _inspire_hit("Good:2000ab", doi="10.1/good", eprint="0001.0001", year=2000, title="")
    # Both entries are in a single batch request; only Good:2000ab is found.
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": [good_hit]}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = check_entries(entries, client=client)

    statuses = {r.key: r.status for r in results}
    assert statuses["Good:2000ab"] == "ok"
    assert statuses["Missing:9999xx"] == "missing"


@rsps_lib.activate
def test_lookup_by_texkeys_batches_requests():
    """Verify lookup_by_texkeys splits large lists into chunks."""
    keys_batch1 = [f"Key:000{i}" for i in range(3)]
    keys_batch2 = [f"Key:010{i}" for i in range(2)]
    all_keys = keys_batch1 + keys_batch2

    hits_batch1 = [_inspire_hit(k, doi="", eprint="", year=2020, title="") for k in keys_batch1]
    hits_batch2 = [_inspire_hit(k, doi="", eprint="", year=2021, title="") for k in keys_batch2]

    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": hits_batch1}}, status=200)
    rsps_lib.add(rsps_lib.GET, _BASE, json={"hits": {"hits": hits_batch2}}, status=200)

    client = InspireClient(rate_limit_delay=0)
    results = client.lookup_by_texkeys(all_keys, batch_size=3)

    assert set(results.keys()) == set(all_keys)
    assert len(rsps_lib.calls) == 2  # two batches fired

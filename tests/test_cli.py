"""Tests for bib_checker.cli — exercises the subcommand dispatch without network calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bib_checker.cli import cmd_fix

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SIMPLE_BIB = """\
@article{Good:2000ab,
    author = "Test, Author",
    title = "{A good paper}",
    doi = "10.1/good",
    eprint = "0001.0001",
    year = "2000"
}
"""

_INSPIRE_RECORD = {
    "id": "99999",
    "metadata": {
        "texkeys": ["Good:2000ab"],
        "titles": [{"title": "A good paper"}],
        "dois": [{"value": "10.1/good"}],
        "arxiv_eprints": [{"value": "0001.0001"}],
        "publication_info": [{"year": 2001}],
        "authors": [{"full_name": "Test, Author"}],
    },
}


def _fix_args(bib: str, results: str, **kwargs) -> argparse.Namespace:
    defaults = {
        "bib_file": bib,
        "results_file": results,
        "output": None,
        "fields": "doi,eprint,year,title",
        "dry_run": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_mismatch_results(path: Path) -> Path:
    results = [
        {
            "key": "Good:2000ab",
            "status": "mismatch",
            "nonstandard_key": False,
            "mismatches": [{"field": "year", "local": "2000", "remote": "2001"}],
            "local_entry": {"key": "Good:2000ab", "type": "article", "year": "2000"},
            "inspire_record": _INSPIRE_RECORD,
            "ads_record": None,
        }
    ]
    p = path / "results.json"
    p.write_text(json.dumps(results))
    return p


# ---------------------------------------------------------------------------
# cmd_fix — success paths
# ---------------------------------------------------------------------------


def test_cmd_fix_returns_zero_on_success(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = _write_mismatch_results(tmp_path)
    rc = cmd_fix(_fix_args(str(bib), str(results)))
    assert rc == 0


def test_cmd_fix_writes_fixed_bib(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = _write_mismatch_results(tmp_path)
    cmd_fix(_fix_args(str(bib), str(results)))
    assert (tmp_path / "paper_fixed.bib").exists()


def test_cmd_fix_custom_output_path(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = _write_mismatch_results(tmp_path)
    out = str(tmp_path / "custom_out.bib")
    cmd_fix(_fix_args(str(bib), str(results), output=out))
    assert Path(out).exists()


def test_cmd_fix_nothing_to_fix_returns_zero(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = tmp_path / "results.json"
    results.write_text("[]")
    rc = cmd_fix(_fix_args(str(bib), str(results)))
    assert rc == 0


# ---------------------------------------------------------------------------
# cmd_fix — dry run
# ---------------------------------------------------------------------------


def test_cmd_fix_dry_run_does_not_write(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = _write_mismatch_results(tmp_path)
    cmd_fix(_fix_args(str(bib), str(results), dry_run=True))
    assert not (tmp_path / "paper_fixed.bib").exists()


# ---------------------------------------------------------------------------
# cmd_fix — error paths
# ---------------------------------------------------------------------------


def test_cmd_fix_missing_bib_returns_one(tmp_path):
    results = tmp_path / "results.json"
    results.write_text("[]")
    rc = cmd_fix(_fix_args(str(tmp_path / "nonexistent.bib"), str(results)))
    assert rc == 1


def test_cmd_fix_missing_results_returns_one(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    rc = cmd_fix(_fix_args(str(bib), str(tmp_path / "missing_results.json")))
    assert rc == 1


def test_cmd_fix_corrupt_results_returns_one(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = tmp_path / "results.json"
    results.write_text("not valid json {{{")
    rc = cmd_fix(_fix_args(str(bib), str(results)))
    assert rc == 1


# ---------------------------------------------------------------------------
# cmd_fix — field filtering
# ---------------------------------------------------------------------------


def test_cmd_fix_field_filtering(tmp_path):
    bib = tmp_path / "paper.bib"
    bib.write_text(_SIMPLE_BIB)
    results = _write_mismatch_results(tmp_path)
    out = tmp_path / "paper_fixed.bib"
    cmd_fix(_fix_args(str(bib), str(results), fields="year"))
    content = out.read_text()
    # Year should be updated to 2001 from InspireHEP
    assert "2001" in content

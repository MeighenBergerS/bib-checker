"""Tests for bib_checker.report."""

from __future__ import annotations

from bib_checker.models import CheckResult, FieldMismatch, Suggestion
from bib_checker.report import write_html_report


def _suggestion(for_key: str, texkey: str = "Real:2008ab") -> Suggestion:
    return Suggestion(
        for_key=for_key,
        texkey=texkey,
        title="The real paper",
        local_title="The local title",
        authors=["Author, A", "Author, B"],
        year="2008",
        doi="10.1/real",
        eprint="0800.0001",
        inspire_id="12345",
    )


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------


def test_report_creates_html_file(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([CheckResult(key="Good:2000ab", status="ok")], [], "test.bib", out)
    assert out.exists()


def test_report_is_valid_html(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([], [], "test.bib", out)
    content = out.read_text()
    assert content.strip().startswith("<!DOCTYPE html>")
    assert "</html>" in content


# ---------------------------------------------------------------------------
# Check results section
# ---------------------------------------------------------------------------


def test_report_contains_missing_key(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([CheckResult(key="Missing:9999xx", status="missing")], [], "test.bib", out)
    assert "Missing:9999xx" in out.read_text()


def test_report_contains_mismatch_key_and_field(tmp_path):
    out = tmp_path / "report.html"
    write_html_report(
        [
            CheckResult(
                key="Spolyar:2007qv",
                status="mismatch",
                mismatches=[FieldMismatch("year", "2009", "2008")],
            )
        ],
        [],
        "test.bib",
        out,
    )
    content = out.read_text()
    assert "Spolyar:2007qv" in content
    assert "year" in content
    assert "2009" in content
    assert "2008" in content


def test_report_ok_only_shows_all_ok_banner(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([CheckResult(key="Good:2000ab", status="ok")], [], "test.bib", out)
    assert "all-ok" in out.read_text()


def test_report_bib_name_in_title(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([], [], "my_paper.bib", out)
    assert "my_paper.bib" in out.read_text()


# ---------------------------------------------------------------------------
# Suggestions section
# ---------------------------------------------------------------------------


def test_report_includes_suggestion_texkey(tmp_path):
    out = tmp_path / "report.html"
    write_html_report(
        [CheckResult(key="Missing:9999xx", status="missing")],
        [_suggestion("Missing:9999xx", "Real:2008ab")],
        "test.bib",
        out,
    )
    assert "Real:2008ab" in out.read_text()


def test_report_includes_inspire_link(tmp_path):
    out = tmp_path / "report.html"
    write_html_report(
        [CheckResult(key="Missing:9999xx", status="missing")],
        [_suggestion("Missing:9999xx")],
        "test.bib",
        out,
    )
    assert "inspirehep.net/literature/12345" in out.read_text()


def test_report_no_suggestions_shows_notice(tmp_path):
    out = tmp_path / "report.html"
    write_html_report(
        [CheckResult(key="Missing:9999xx", status="missing")],
        [],
        "test.bib",
        out,
    )
    assert "no-suggestions" in out.read_text()


def test_report_multiple_results(tmp_path):
    out = tmp_path / "report.html"
    results = [
        CheckResult(key="Good:2000ab", status="ok"),
        CheckResult(key="Missing:9999xx", status="missing"),
        CheckResult(
            key="Mismatch:2010ab",
            status="mismatch",
            mismatches=[FieldMismatch("doi", "10.1/old", "10.1/new")],
        ),
    ]
    write_html_report(results, [], "test.bib", out)
    content = out.read_text()
    assert "Missing:9999xx" in content
    assert "Mismatch:2010ab" in content


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_report_empty_results_and_suggestions(tmp_path):
    out = tmp_path / "report.html"
    write_html_report([], [], "empty.bib", out)
    assert out.exists()


def test_report_html_escapes_special_chars(tmp_path):
    out = tmp_path / "report.html"
    results = [
        CheckResult(
            key="Test:2000ab",
            status="mismatch",
            mismatches=[FieldMismatch("title", "<script>alert(1)</script>", "safe title")],
        )
    ]
    write_html_report(results, [], "test.bib", out)
    content = out.read_text()
    assert "<script>alert(1)</script>" not in content
    assert "&lt;script&gt;" in content

"""Generate a self-contained HTML report of check results and suggestions."""

from __future__ import annotations

import html
from datetime import UTC, datetime
from pathlib import Path

from .models import CheckResult, Suggestion

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    background: #0f1117;
    color: #e2e8f0;
    padding: 2rem;
    line-height: 1.5;
}

h1 { font-size: 1.6rem; font-weight: 700; color: #f8fafc; margin-bottom: .25rem; }
h2 { font-size: 1.15rem; font-weight: 600; color: #94a3b8; margin: 2rem 0 .75rem; }
h3 { font-size: 1rem; font-weight: 600; color: #7dd3fc; margin: 1.5rem 0 .4rem; }

.subtitle { color: #64748b; font-size: .85rem; margin-bottom: 1.5rem; }

/* Summary pills */
.summary {
    display: flex;
    gap: .75rem;
    flex-wrap: wrap;
    margin-bottom: 2rem;
}
.pill {
    padding: .35rem .9rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: .9rem;
    letter-spacing: .02em;
}
.pill-ok        { background: #14532d; color: #86efac; }
.pill-missing   { background: #450a0a; color: #fca5a5; }
.pill-mismatch  { background: #451a03; color: #fcd34d; }
.pill-nonstd    { background: #2e1065; color: #d8b4fe; }

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1.5rem;
    background: #1e2433;
    border-radius: 8px;
    overflow: hidden;
}
thead th {
    background: #2d3748;
    color: #94a3b8;
    text-align: left;
    padding: .55rem .85rem;
    font-size: .78rem;
    text-transform: uppercase;
    letter-spacing: .06em;
    font-weight: 600;
}
tbody tr { border-bottom: 1px solid #2d3748; }
tbody tr:last-child { border-bottom: none; }
tbody tr:hover { background: #252d3d; }
td { padding: .55rem .85rem; vertical-align: top; }

/* Status badges */
.badge {
    display: inline-block;
    padding: .2rem .55rem;
    border-radius: 4px;
    font-size: .78rem;
    font-weight: 700;
    white-space: nowrap;
}
.badge-ok       { background: #14532d; color: #86efac; }
.badge-missing  { background: #450a0a; color: #fca5a5; }
.badge-mismatch { background: #451a03; color: #fcd34d; }
.badge-nonstd   { background: #2e1065; color: #d8b4fe; }

/* Mismatch diff block */
.mismatch-field { margin-bottom: .5rem; }
.mismatch-field:last-child { margin-bottom: 0; }
.field-name { font-weight: 600; color: #c084fc; font-size: .8rem; margin-bottom: .15rem; }
.diff-row { display: flex; gap: .5rem; font-size: .8rem; align-items: baseline; }
.diff-label {
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .05em;
    min-width: 3.5rem;
    color: #64748b;
}
.diff-local   { color: #fca5a5; }
.diff-inspire { color: #86efac; }

/* Key column */
.key { font-family: "JetBrains Mono", "Fira Code", monospace; color: #7dd3fc; font-size: .85rem; }

/* Suggestion group */
.suggest-group { margin-bottom: 2.5rem; }
.local-title {
    font-size: .82rem;
    color: #94a3b8;
    margin-bottom: .5rem;
}
.local-title span { color: #e2e8f0; font-style: italic; }

.suggest-num { color: #475569; font-size: .8rem; }
.suggest-texkey { font-family: "JetBrains Mono", "Fira Code", monospace; color: #7dd3fc; font-size: .82rem; }
.suggest-ref { font-family: "JetBrains Mono", "Fira Code", monospace; font-size: .78rem; color: #818cf8; }
.suggest-ref a { color: #818cf8; text-decoration: none; }
.suggest-ref a:hover { text-decoration: underline; }

/* All-ok banner */
.all-ok {
    padding: 1rem 1.25rem;
    background: #14532d;
    border-radius: 8px;
    color: #86efac;
    font-weight: 600;
    margin-bottom: 1.5rem;
}

/* No-suggestions notice */
.no-suggestions {
    padding: .75rem 1rem;
    background: #1e2433;
    border-radius: 8px;
    color: #64748b;
}

footer {
    margin-top: 3rem;
    color: #334155;
    font-size: .75rem;
    border-top: 1px solid #1e2433;
    padding-top: .75rem;
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _e(s: str) -> str:
    """HTML-escape a string."""
    return html.escape(s or "")


def _inspire_url(record: dict | None) -> str:
    """Return the InspireHEP URL for a record, or empty string."""
    if not record:
        return ""
    rid = record.get("id") or record.get("metadata", {}).get("control_number", "")
    return f"https://inspirehep.net/literature/{rid}" if rid else ""


def _ref_cell(eprint: str, doi: str) -> str:
    """Render eprint / DOI as a linked cell."""
    if eprint:
        url = f"https://arxiv.org/abs/{eprint}"
        return f'<a href="{_e(url)}">{_e(eprint)}</a>'
    if doi:
        url = f"https://doi.org/{doi}"
        return f'<a href="{_e(url)}">{_e(doi)}</a>'
    return "—"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_check_section(results: list[CheckResult], bib_name: str) -> str:
    ok = [r for r in results if r.status == "ok"]
    missing = [r for r in results if r.status == "missing"]
    mismatch = [r for r in results if r.status == "mismatch"]
    nonstandard = [r for r in results if r.nonstandard_key]
    flagged = missing + mismatch

    pills = (
        f'<span class="pill pill-ok">✓ {len(ok)} ok</span>'
        f'<span class="pill pill-missing">✗ {len(missing)} missing</span>'
        f'<span class="pill pill-mismatch">~ {len(mismatch)} mismatched</span>'
    )
    if nonstandard:
        pills += f'<span class="pill pill-nonstd">⚠ {len(nonstandard)} non-standard key(s)</span>'

    if not flagged:
        body = '<div class="all-ok">✓ All entries look good.</div>'
    else:
        rows = []
        for r in flagged:
            badge_cls = "badge-missing" if r.status == "missing" else "badge-mismatch"
            badge_sym = "✗" if r.status == "missing" else "~"
            badge = f'<span class="badge {badge_cls}">{badge_sym} {r.status}</span>'
            if r.nonstandard_key:
                badge += ' <span class="badge badge-nonstd">⚠ non-std key</span>'

            if r.mismatches:
                parts = []
                for m in r.mismatches:
                    parts.append(
                        f'<div class="mismatch-field">'
                        f'<div class="field-name">{_e(m.field_name)}</div>'
                        f'<div class="diff-row">'
                        f'<span class="diff-label">local</span>'
                        f'<span class="diff-local">{_e(m.local_value) or "—"}</span>'
                        f"</div>"
                        f'<div class="diff-row">'
                        f'<span class="diff-label">remote</span>'
                        f'<span class="diff-inspire">{_e(m.remote_value) or "—"}</span>'
                        f"</div>"
                        f"</div>"
                    )
                details = "".join(parts)
            else:
                details = '<span style="color:#475569">—</span>'

            rows.append(
                f'<tr><td class="key">{_e(r.key)}</td><td>{badge}</td><td>{details}</td></tr>'
            )

        body = (
            "<table>"
            "<thead><tr>"
            "<th>Citation key</th><th>Status</th><th>Mismatched fields</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

    return (
        f"<h1>bib-checker report: {_e(bib_name)}</h1>\n"
        f'<div class="summary">{pills}</div>\n'
        f"<h2>Flagged entries</h2>\n"
        f"{body}\n"
    )


def _build_suggestions_section(suggestions: list[Suggestion]) -> str:
    if not suggestions:
        return (
            "<h2>Replacement suggestions</h2>\n"
            '<div class="no-suggestions">No suggestions — nothing was flagged.</div>\n'
        )

    by_key: dict[str, list[Suggestion]] = {}
    for s in suggestions:
        by_key.setdefault(s.for_key, []).append(s)

    groups = []
    for for_key, group in by_key.items():
        local_title = group[0].local_title or "(no title in bib)"

        rows = []
        for i, s in enumerate(group, start=1):
            first_author = _e(s.authors[0]) if s.authors else "—"
            ref = _ref_cell(s.eprint, s.doi)
            inspire_link = ""
            if s.inspire_id:
                url = f"https://inspirehep.net/literature/{s.inspire_id}"
                inspire_link = f' <a href="{url}" style="font-size:.7rem;color:#475569">↗</a>'

            rows.append(
                f"<tr>"
                f'<td class="suggest-num">{i}</td>'
                f'<td class="suggest-texkey">{_e(s.texkey)}{inspire_link}</td>'
                f"<td>{_e(s.title)}</td>"
                f"<td>{first_author}</td>"
                f'<td style="text-align:center">{_e(s.year)}</td>'
                f'<td class="suggest-ref">{ref}</td>'
                f"</tr>"
            )

        table = (
            "<table>"
            "<thead><tr>"
            "<th>#</th><th>Texkey</th><th>Suggested title</th>"
            "<th>First author</th><th>Year</th><th>Eprint / DOI</th>"
            "</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )

        groups.append(
            f'<div class="suggest-group">'
            f"<h3>Suggestions for {_e(for_key)}</h3>"
            f'<div class="local-title">Local title: <span>{_e(local_title)}</span></div>'
            f"{table}"
            f"</div>"
        )

    return "<h2>Replacement suggestions</h2>\n" + "\n".join(groups)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_html_report(
    results: list[CheckResult],
    suggestions: list[Suggestion],
    bib_name: str,
    output_path: str | Path,
) -> None:
    """Write a self-contained HTML report combining check results and suggestions.

    Parameters
    ----------
    results : list[CheckResult]
        Results from :func:`~bib_checker.checker.check_entries`.
    suggestions : list[Suggestion]
        Suggestions from :func:`~bib_checker.searcher.suggest_replacements`.
        Pass an empty list when Step 2 was not run.
    bib_name : str
        Display name for the source .bib file.
    output_path : str or Path
        Where to write the ``.html`` file.
    """
    output_path = Path(output_path)
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M UTC")

    check_section = _build_check_section(results, bib_name)
    suggest_section = _build_suggestions_section(suggestions)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bib-checker — {_e(bib_name)}</title>
<style>{_CSS}</style>
</head>
<body>
{check_section}
{suggest_section}
<footer>Generated by bib-checker on {now}</footer>
</body>
</html>
"""
    output_path.write_text(page, encoding="utf-8")

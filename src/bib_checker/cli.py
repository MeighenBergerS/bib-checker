"""CLI entry points for bib-checker (check and suggest subcommands)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .cache import CheckCache
from .checker import check_entries
from .config import load_ignore_keys
from .display import console, print_check_results, print_suggestions
from .fixer import DEFAULT_FIX_FIELDS, apply_fixes
from .inspire import InspireClient
from .parser import parse_bib_file, write_reformatted_bib
from .report import write_html_report
from .searcher import suggest_replacements

# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    """Run the check subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    exit_code : int
        0 on success, 1 on error.
    """
    bib_path = Path(args.bib_file)

    try:
        entries = parse_bib_file(bib_path)
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return 1

    console.print(f"Parsed [bold]{len(entries)}[/] entries from [cyan]{bib_path.name}[/]")

    client = InspireClient(rate_limit_delay=args.delay)

    # Set up ADS client if a token is available.
    ads_token = args.ads_token or os.environ.get("ADS_TOKEN", "")
    ads_client = None
    if ads_token:
        from .ads import AdsClient

        ads_client = AdsClient(ads_token, rate_limit_delay=args.delay)
    elif args.verbose:
        console.print(
            "  [dim]No ADS token — skipping ADS direct fallback "
            "(set ADS_TOKEN or pass --ads-token).[/]"
        )

    # Load ignore list from pyproject.toml / .bibcheckerignore.
    ignore_keys = load_ignore_keys(bib_path)
    if ignore_keys and args.verbose:
        console.print(f"  Ignoring [bold]{len(ignore_keys)}[/] key(s) from config.")

    # Set up cache (unless --no-cache was passed).
    cache: CheckCache | None = None
    if not args.no_cache:
        cache = CheckCache(CheckCache.default_path(bib_path))

    results = check_entries(
        entries,
        client=client,
        ads_client=ads_client,
        verbose=args.verbose,
        cache=cache,
        ignore_keys=ignore_keys,
    )

    print_check_results(results, bib_path.name)

    _FLAGGED = ("missing", "mismatch", "found_via_ads", "mismatch_via_ads")
    output = [r.to_dict() for r in results if r.status in _FLAGGED]
    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    console.print(f"Wrote [bold]{len(output)}[/] flagged entries to [cyan]{out_path}[/]\n")

    if args.reformat:
        flagged_keys = {r.key for r in results if r.status in ("missing", "mismatch")}
        reformat_out = args.reformat_output or bib_path.with_name(
            bib_path.stem + "_reformatted" + bib_path.suffix
        )
        reformat_path = Path(reformat_out)
        n_ok, n_bad = write_reformatted_bib(bib_path, flagged_keys, reformat_path)
        console.print(
            f"Wrote reformatted bib to [cyan]{reformat_path}[/] "
            f"([green]{n_ok} ok[/] + [yellow]{n_bad} flagged[/])\n"
        )

    if args.html:
        html_out = args.html_output or bib_path.with_name(bib_path.stem + "_report.html")
        write_html_report(results, [], bib_path.name, html_out)
        console.print(f"Wrote HTML report to [cyan]{html_out}[/]\n")

    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    """Run the suggest subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    exit_code : int
        0 on success, 1 on error.
    """
    results_path = Path(args.results_file)
    if not results_path.exists():
        console.print(f"[bold red]Error:[/] {results_path} not found")
        return 1

    client = InspireClient(rate_limit_delay=args.delay)

    try:
        suggestions = suggest_replacements(results_path, client=client, verbose=args.verbose)
    except (json.JSONDecodeError, KeyError) as exc:
        console.print(f"[bold red]Error reading results file:[/] {exc}")
        return 1

    print_suggestions(suggestions)

    out_path = Path(args.output)
    out_path.write_text(
        json.dumps([s.to_dict() for s in suggestions], indent=2, ensure_ascii=False)
    )
    console.print(f"Wrote [bold]{len(suggestions)}[/] suggestions to [cyan]{out_path}[/]\n")

    if args.html:
        # Reload check results so the HTML report is fully combined.
        import bib_checker.models as _m

        raw_results = json.loads(results_path.read_text())
        check_results = [
            _m.CheckResult(
                key=r["key"],
                status=r["status"],
                mismatches=[
                    _m.FieldMismatch(
                        field_name=m["field"],
                        local_value=m["local"],
                        remote_value=m["remote"],
                    )
                    for m in r.get("mismatches", [])
                ],
                local_entry=r.get("local_entry"),
                inspire_record=r.get("inspire_record"),
            )
            for r in raw_results
        ]
        bib_name = results_path.stem.replace("_results", "") or results_path.stem
        html_out = args.html_output or results_path.with_name(
            results_path.stem.replace("results", "report") + ".html"
        )
        write_html_report(check_results, suggestions, bib_name, html_out)
        console.print(f"Wrote HTML report to [cyan]{html_out}[/]\n")

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def cmd_fix(args: argparse.Namespace) -> int:
    """Run the fix subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    exit_code : int
        0 on success, 1 on error.
    """
    bib_path = Path(args.bib_file)
    results_path = Path(args.results_file)

    for p in (bib_path, results_path):
        if not p.exists():
            console.print(f"[bold red]Error:[/] {p} not found")
            return 1

    import json as _json

    try:
        results = _json.loads(results_path.read_text())
    except _json.JSONDecodeError as exc:
        console.print(f"[bold red]Error reading results file:[/] {exc}")
        return 1

    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    output_path = Path(args.output) if args.output else None

    try:
        applied = apply_fixes(
            bib_path,
            results,
            output_path=output_path,
            fields=fields,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        return 1

    if not applied:
        console.print("[green]Nothing to fix — no mismatch entries with known records.[/]")
        return 0

    dest = output_path or bib_path
    verb = "Would update" if args.dry_run else "Updated"
    console.print(f"{verb} [bold]{len(applied)}[/] field(s) in [cyan]{dest}[/]:\n")

    for change in applied:
        console.print(
            f"  [cyan]{change['key']}[/]  [bold]{change['field']}[/]\n"
            f"    [red]- {change['old'] or '(empty)'}[/]\n"
            f"    [green]+ {change['new']}[/]\n"
        )

    if args.dry_run:
        console.print("[yellow]Dry run — no files were modified.[/]")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level argument parser.

    Returns
    -------
    parser : argparse.ArgumentParser
        Configured parser with check and suggest subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="bib-checker",
        description="Validate .bib citations against InspireHEP.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        metavar="SECONDS",
        help="Delay between API requests (default: 0.5 s).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print progress for each entry."
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # -- check ---------------------------------------------------------------
    p_check = sub.add_parser(
        "check",
        help="Step 1: check entries and write flagged ones to JSON.",
    )
    p_check.add_argument("bib_file", metavar="FILE.bib")
    p_check.add_argument(
        "--output",
        "-o",
        default="results.json",
        metavar="FILE",
        help="Output JSON file (default: results.json).",
    )
    p_check.add_argument(
        "--reformat",
        action="store_true",
        help="Write a reformatted .bib file with flagged entries moved to the end.",
    )
    p_check.add_argument(
        "--reformat-output",
        default=None,
        metavar="FILE",
        help="Output path for the reformatted .bib file (default: <name>_reformatted.bib).",
    )
    p_check.add_argument(
        "--html",
        action="store_true",
        help="Write a self-contained HTML report alongside the JSON output.",
    )
    p_check.add_argument(
        "--html-output",
        default=None,
        metavar="FILE",
        help="Output path for the HTML report (default: <name>_report.html).",
    )
    p_check.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass the on-disk result cache and re-fetch everything.",
    )
    p_check.add_argument(
        "--ads-token",
        default=None,
        metavar="TOKEN",
        help="NASA ADS API token for direct ADS fallback (overrides ADS_TOKEN env var).",
    )
    p_check.set_defaults(func=cmd_check)

    # -- suggest -------------------------------------------------------------
    p_suggest = sub.add_parser(
        "suggest",
        help="Step 2: load flagged entries and search for replacements.",
    )
    p_suggest.add_argument("results_file", metavar="results.json")
    p_suggest.add_argument(
        "--output",
        "-o",
        default="suggestions.json",
        metavar="FILE",
        help="Output JSON file (default: suggestions.json).",
    )
    p_suggest.add_argument(
        "--html",
        action="store_true",
        help="Write a combined HTML report (check results + suggestions).",
    )
    p_suggest.add_argument(
        "--html-output",
        default=None,
        metavar="FILE",
        help="Output path for the HTML report (default: report.html next to results.json).",
    )
    p_suggest.set_defaults(func=cmd_suggest)

    # -- fix ----------------------------------------------------------------
    p_fix = sub.add_parser(
        "fix",
        help="Step 3: apply InspireHEP canonical values to mismatch entries.",
    )
    p_fix.add_argument("bib_file", metavar="FILE.bib")
    p_fix.add_argument(
        "results_file",
        metavar="results.json",
        help="results.json produced by the check subcommand.",
    )
    p_fix.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Output .bib path (default: in-place).",
    )
    p_fix.add_argument(
        "--fields",
        default=",".join(DEFAULT_FIX_FIELDS),
        metavar="FIELDS",
        help=f"Comma-separated fields to fix (default: {','.join(DEFAULT_FIX_FIELDS)}).",
    )
    p_fix.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing anything.",
    )
    p_fix.set_defaults(func=cmd_fix)

    return parser


def main() -> None:
    """Entry point for the bib-checker command-line tool."""
    import sys

    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))

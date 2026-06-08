"""CLI entry points for bib-checker (check and suggest subcommands)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checker import check_entries
from .display import console, print_check_results, print_suggestions
from .inspire import InspireClient
from .parser import parse_bib_file, write_reformatted_bib
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
    results = check_entries(entries, client=client, verbose=args.verbose)

    print_check_results(results, bib_path.name)

    output = [r.to_dict() for r in results if r.status in ("missing", "mismatch")]
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

    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


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
    p_suggest.set_defaults(func=cmd_suggest)

    return parser


def main() -> None:
    """Entry point for the bib-checker command-line tool."""
    import sys

    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))

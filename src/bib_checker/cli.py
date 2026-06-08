"""CLI entry points for bib-checker (check and suggest subcommands)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .checker import check_entries
from .inspire import InspireClient
from .parser import parse_bib_file
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
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Parsed {len(entries)} entries from {bib_path.name}")

    client = InspireClient(rate_limit_delay=args.delay)
    results = check_entries(entries, client=client, verbose=args.verbose)

    ok = sum(1 for r in results if r.status == "ok")
    missing = sum(1 for r in results if r.status == "missing")
    mismatch = sum(1 for r in results if r.status == "mismatch")

    print(f"Results: {ok} ok  |  {missing} missing  |  {mismatch} mismatched")

    output = [r.to_dict() for r in results if r.status in ("missing", "mismatch")]

    out_path = Path(args.output)
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"Wrote {len(output)} flagged entries to {out_path}")

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
        print(f"Error: {results_path} not found", file=sys.stderr)
        return 1

    client = InspireClient(rate_limit_delay=args.delay)

    try:
        suggestions = suggest_replacements(
            results_path, client=client, verbose=args.verbose
        )
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"Error reading results file: {exc}", file=sys.stderr)
        return 1

    out_path = Path(args.output)
    out_path.write_text(
        json.dumps([s.to_dict() for s in suggestions], indent=2, ensure_ascii=False)
    )
    print(f"Wrote {len(suggestions)} suggestions to {out_path}")

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
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))

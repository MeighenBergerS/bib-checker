"""01_basics.py — basic usage of the bib-checker Python API.

This script walks through the two core steps of bib-checker:

  Step 1: parse a .bib file and check every entry against InspireHEP.
  Step 2: for flagged entries, search InspireHEP for replacement candidates.

Run from the repository root with the virtual environment active:

  python examples/01_basics.py

By default the script targets the sample bibliography shipped with the repo.
Pass a path to any .bib file as the first argument to use your own:

  python examples/01_basics.py path/to/my/refs.bib

Note: this script makes live requests to the InspireHEP API.
Expect roughly 0.5 seconds per entry due to rate limiting.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running the script directly without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bib_checker.cache import CheckCache
from bib_checker.checker import check_entries
from bib_checker.config import load_ignore_keys
from bib_checker.display import console, print_check_results, print_suggestions
from bib_checker.inspire import InspireClient
from bib_checker.parser import parse_bib_file, write_reformatted_bib
from bib_checker.report import write_html_report
from bib_checker.searcher import suggest_replacements

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default to the sample bib shipped with the repo; override via argv.
BIB_FILE = (
    Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent / "bibliography.bib"
)

# Output paths written next to the script.
RESULTS_FILE = Path(__file__).parent / "results.json"
SUGGESTIONS_FILE = Path(__file__).parent / "suggestions.json"
HTML_REPORT_FILE = Path(__file__).parent / "report.html"
REFORMATTED_FILE = BIB_FILE.with_name(BIB_FILE.stem + "_reformatted" + BIB_FILE.suffix)

# ---------------------------------------------------------------------------
# Step 1: parse and check
# ---------------------------------------------------------------------------

console.print(f"Parsing [cyan]{BIB_FILE}[/] …")
entries = parse_bib_file(BIB_FILE)
console.print(f"  Found [bold]{len(entries)}[/] entries.\n")

client = InspireClient(rate_limit_delay=0.5)

console.print("Checking entries against InspireHEP …")
ignore_keys = load_ignore_keys(BIB_FILE)
cache = CheckCache(CheckCache.default_path(BIB_FILE))
results = check_entries(
    entries,
    client=client,
    verbose=True,
    cache=cache,
    ignore_keys=ignore_keys,
)

print_check_results(results, BIB_FILE.name)

# Write flagged entries to JSON.
flagged = [r.to_dict() for r in results if r.status in ("missing", "mismatch")]
RESULTS_FILE.write_text(json.dumps(flagged, indent=2, ensure_ascii=False))
console.print(f"Wrote [bold]{len(flagged)}[/] flagged entries → [cyan]{RESULTS_FILE}[/]\n")

# Write reformatted bib with flagged entries moved to the end.
flagged_keys = {r.key for r in results if r.status in ("missing", "mismatch")}
n_ok, n_bad = write_reformatted_bib(BIB_FILE, flagged_keys, REFORMATTED_FILE)
console.print(
    f"Wrote reformatted bib → [cyan]{REFORMATTED_FILE}[/] "
    f"([green]{n_ok} ok[/] + [yellow]{n_bad} flagged[/])\n"
)

# ---------------------------------------------------------------------------
# Step 2: search for replacements (only when there is something to fix)
# ---------------------------------------------------------------------------

if not flagged:
    console.print("[green]All entries look good — nothing to suggest.[/]")
    write_html_report(results, [], BIB_FILE.name, HTML_REPORT_FILE)
    console.print(f"Wrote HTML report → [cyan]{HTML_REPORT_FILE}[/]")
    sys.exit(0)

console.print("Searching InspireHEP for replacement candidates …")
suggestions = suggest_replacements(RESULTS_FILE, client=client, verbose=True)

print_suggestions(suggestions)

SUGGESTIONS_FILE.write_text(
    json.dumps([s.to_dict() for s in suggestions], indent=2, ensure_ascii=False)
)
console.print(f"Wrote [bold]{len(suggestions)}[/] suggestions → [cyan]{SUGGESTIONS_FILE}[/]")

# Write combined HTML report.
write_html_report(results, suggestions, BIB_FILE.name, HTML_REPORT_FILE)
console.print(f"Wrote HTML report → [cyan]{HTML_REPORT_FILE}[/]")

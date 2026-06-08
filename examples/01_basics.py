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

from bib_checker.checker import check_entries
from bib_checker.inspire import InspireClient
from bib_checker.parser import parse_bib_file
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

# ---------------------------------------------------------------------------
# Step 1: parse and check
# ---------------------------------------------------------------------------

print(f"Parsing {BIB_FILE} …")
entries = parse_bib_file(BIB_FILE)
print(f"  Found {len(entries)} entries.\n")

client = InspireClient(rate_limit_delay=0.5)

print("Checking entries against InspireHEP …")
results = check_entries(entries, client=client, verbose=True)

ok = [r for r in results if r.status == "ok"]
missing = [r for r in results if r.status == "missing"]
mismatch = [r for r in results if r.status == "mismatch"]

print(f"\nResults: {len(ok)} ok  |  {len(missing)} missing  |  {len(mismatch)} mismatched")

# Write flagged entries to JSON.
flagged = [r.to_dict() for r in missing + mismatch]
RESULTS_FILE.write_text(json.dumps(flagged, indent=2, ensure_ascii=False))
print(f"Wrote {len(flagged)} flagged entries → {RESULTS_FILE}\n")

# ---------------------------------------------------------------------------
# Step 2: search for replacements (only when there is something to fix)
# ---------------------------------------------------------------------------

if not flagged:
    print("All entries look good — nothing to suggest.")
    sys.exit(0)

print("Searching InspireHEP for replacement candidates …")
suggestions = suggest_replacements(RESULTS_FILE, client=client, verbose=True)

SUGGESTIONS_FILE.write_text(
    json.dumps([s.to_dict() for s in suggestions], indent=2, ensure_ascii=False)
)
print(f"\nWrote {len(suggestions)} suggestions → {SUGGESTIONS_FILE}")

# ---------------------------------------------------------------------------
# Pretty-print a short summary of suggestions
# ---------------------------------------------------------------------------

if suggestions:
    print("\n--- Suggestions ---")
    current_key = None
    for s in suggestions:
        if s.for_key != current_key:
            print(f"\n  For '{s.for_key}':")
            current_key = s.for_key
        first_author = s.authors[0] if s.authors else "Unknown"
        print(f"    [{s.texkey}] {s.title[:70]} — {first_author} ({s.year})")

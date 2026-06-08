"""Step 2: for entries flagged as missing or mismatched, search InspireHEP
for likely replacements.

Search strategy (applied in priority order, first hit wins):
  1. arXiv eprint ID  (most precise)
  2. DOI
  3. First author surname + year
If none of those fields are available, the entry is skipped.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .inspire import InspireClient
from .models import Suggestion


def _first_surname(author_str: str) -> str:
    """Extract the surname of the first author from a 'Last, First and …' string."""
    first = author_str.split(" and ")[0].strip()
    # Handle "Last, First" and "First Last" formats.
    if "," in first:
        return first.split(",")[0].strip()
    parts = first.split()
    return parts[-1] if parts else first


def _build_queries(entry: dict[str, Any]) -> list[str]:
    """Return candidate search queries in priority order."""
    queries: list[str] = []

    eprint = entry.get("eprint", "").strip()
    if eprint:
        # Strip old-style prefix like "astro-ph/9906391" → use as-is; numeric IDs too.
        queries.append(f"arxiv:{eprint}")

    doi = entry.get("doi", "").strip()
    if doi:
        queries.append(f"doi:{doi}")

    author = entry.get("author", "").strip()
    year = entry.get("year", "").strip()
    if author and year:
        surname = _first_surname(author)
        queries.append(f"a {surname} and date {year}")

    return queries


def _record_to_suggestion(for_key: str, record: dict[str, Any]) -> Suggestion:
    return Suggestion(
        for_key=for_key,
        texkey=InspireClient.get_texkey(record),
        title=InspireClient.get_title(record),
        authors=InspireClient.get_authors(record),
        year=InspireClient.get_year(record),
        doi=InspireClient.get_doi(record),
        eprint=InspireClient.get_eprint(record),
        inspire_id=InspireClient.get_inspire_id(record),
    )


def suggest_replacements(
    results_path: str | Path,
    client: InspireClient | None = None,
    verbose: bool = False,
) -> list[Suggestion]:
    """Load *results_path* (Step 1 output) and search for replacements.

    Only entries with status "missing" or "mismatch" are processed.
    Returns a flat list of Suggestion objects (up to 5 per entry).
    """
    if client is None:
        client = InspireClient()

    results_path = Path(results_path)
    with results_path.open() as fh:
        results: list[dict[str, Any]] = json.load(fh)

    actionable = [r for r in results if r.get("status") in ("missing", "mismatch")]

    suggestions: list[Suggestion] = []

    for i, result in enumerate(actionable, start=1):
        key = result["key"]
        local = result.get("local_entry") or {}

        if verbose:
            print(f"[{i}/{len(actionable)}] Searching for {key} …")

        queries = _build_queries(local)
        found: list[dict[str, Any]] = []

        for query in queries:
            hits = client.search(query, size=5)
            if hits:
                found = hits
                break  # first successful strategy wins

        for record in found:
            suggestions.append(_record_to_suggestion(key, record))

    return suggestions

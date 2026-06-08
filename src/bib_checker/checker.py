"""Step 1: check bib entries against InspireHEP.

Entries not found by texkey are flagged as ``"missing"``.
Entries where key fields differ are flagged as ``"mismatch"``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .cache import CheckCache
from .inspire import InspireClient
from .models import BibEntry, CheckResult, FieldMismatch

# Fields we compare between the local bib and InspireHEP.
# Each tuple is (local_field_name, extractor_method_name_on_InspireClient).
_COMPARED_FIELDS: list[tuple[str, str]] = [
    ("doi", "get_doi"),
    ("eprint", "get_eprint"),
    ("year", "get_year"),
    ("title", "get_title"),
]

# InspireHEP canonical texkey pattern: Author:YYYYxx or COLLAB:YYYYabc.
# The suffix is 2 or more lowercase letters.
# Examples that match: Spolyar:2007qv, ATLAS:2021abc, CMS:2023zz
# Examples that don't: chan2024first, Balaji_2023
_TEXKEY_RE = re.compile(r"^[A-Za-z][A-Za-z]*:\d{4}[a-z]{2,}$")


def _normalise(value: str) -> str:
    """Lower-case, strip, collapse whitespace, and drop accents for comparison."""
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return " ".join(value.lower().split())


def _compare_fields(
    entry: BibEntry,
    record: dict[str, Any],
    client: InspireClient,
) -> list[FieldMismatch]:
    """Compare selected fields of *entry* against *record*.

    Parameters
    ----------
    entry : BibEntry
        Local bib entry to compare.
    record : dict[str, Any]
        Raw InspireHEP API hit dict.
    client : InspireClient
        Client instance (used only for its static extractor methods).

    Returns
    -------
    mismatches : list[FieldMismatch]
        Fields whose normalised values differ between entry and record.
    """
    mismatches: list[FieldMismatch] = []
    for local_field, extractor in _COMPARED_FIELDS:
        local_val = _normalise(entry.fields.get(local_field, ""))
        inspire_val = _normalise(getattr(InspireClient, extractor)(record))
        if local_val and inspire_val and local_val != inspire_val:
            mismatches.append(
                FieldMismatch(
                    field_name=local_field,
                    local_value=entry.fields.get(local_field, ""),
                    inspire_value=getattr(InspireClient, extractor)(record),
                )
            )
    return mismatches


def check_entries(
    entries: list[BibEntry],
    client: InspireClient | None = None,
    verbose: bool = False,
    batch_size: int = 50,
    cache: CheckCache | None = None,
    ignore_keys: set[str] | None = None,
) -> list[CheckResult]:
    """Check *entries* against InspireHEP and return one result per entry.

    Entries are looked up in batches (OR queries) to minimise the number of
    API requests.  Already-cached results are reused without hitting the API.
    Keys in *ignore_keys* are silently skipped.

    Parameters
    ----------
    entries : list[BibEntry]
        Entries to check, typically parsed from a .bib file.
    client : InspireClient, optional
        API client to use. A default client is created when ``None``.
    verbose : bool, optional
        Print progress to stdout for each batch. Default is ``False``.
    batch_size : int, optional
        Number of texkeys to include per API request. Default is 50.
    cache : CheckCache, optional
        On-disk cache.  When provided, cached results are used and new
        results are written back to the cache after checking.
    ignore_keys : set[str], optional
        Citation keys to skip entirely (no API call, no result).

    Returns
    -------
    results : list[CheckResult]
        One result per non-ignored input entry. Status is ``"ok"``,
        ``"missing"``, or ``"mismatch"``.  The ``nonstandard_key`` flag
        is set when the citation key doesn't follow the InspireHEP
        ``Author:YYYYxx`` convention.
    """
    if client is None:
        client = InspireClient()
    if ignore_keys is None:
        ignore_keys = set()

    # Split entries into cache-hits and those that need a network call.
    to_fetch: list[BibEntry] = []
    cached_results: dict[str, CheckResult] = {}

    for entry in entries:
        if entry.key in ignore_keys:
            continue
        if cache is not None:
            hit = cache.get(entry.key, entry.fields)
            if hit is not None:
                cached_results[entry.key] = hit
                continue
        to_fetch.append(entry)

    n_ignored = len(entries) - len(to_fetch) - len(cached_results)
    n_cached = len(cached_results)

    if verbose and (n_ignored or n_cached):
        print(f"  {n_cached} from cache, {n_ignored} ignored, {len(to_fetch)} to fetch.")

    # Batch-fetch the remaining entries.
    records: dict[str, dict[str, Any]] = {}
    if to_fetch:
        texkeys = [e.key for e in to_fetch]
        n_batches = (len(texkeys) + batch_size - 1) // batch_size
        if verbose:
            print(f"Fetching {len(texkeys)} entries in {n_batches} batch(es) …")
        records = client.lookup_by_texkeys(texkeys, batch_size=batch_size)
        if verbose:
            print(f"  {len(records)} found, {len(texkeys) - len(records)} not found.")

    # Build results in original entry order (skipping ignored keys).
    results: list[CheckResult] = []
    for entry in entries:
        if entry.key in ignore_keys:
            continue

        # Use cached result if available.
        if entry.key in cached_results:
            results.append(cached_results[entry.key])
            continue

        nonstandard = not bool(_TEXKEY_RE.match(entry.key))
        record = records.get(entry.key)

        if record is None:
            result = CheckResult(
                key=entry.key,
                status="missing",
                nonstandard_key=nonstandard,
                local_entry={"key": entry.key, "type": entry.entry_type, **entry.fields},
            )
        else:
            mismatches = _compare_fields(entry, record, client)
            result = CheckResult(
                key=entry.key,
                status="mismatch" if mismatches else "ok",
                nonstandard_key=nonstandard,
                mismatches=mismatches,
                local_entry={"key": entry.key, "type": entry.entry_type, **entry.fields},
                inspire_record=record,
            )

        if cache is not None:
            cache.put(entry.key, entry.fields, result)

        results.append(result)

    if cache is not None:
        cache.save()

    return results

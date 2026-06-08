"""Step 1: check bib entries against InspireHEP.

Entries not found by texkey are flagged as ``"missing"``.
Entries where key fields differ are flagged as ``"mismatch"``.
"""

from __future__ import annotations

import unicodedata
from typing import Any

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
) -> list[CheckResult]:
    """Check *entries* against InspireHEP and return one result per entry.

    Parameters
    ----------
    entries : list[BibEntry]
        Entries to check, typically parsed from a .bib file.
    client : InspireClient, optional
        API client to use. A default client is created when ``None``.
    verbose : bool, optional
        Print progress to stdout for each entry. Default is ``False``.

    Returns
    -------
    results : list[CheckResult]
        One result per input entry. Status is ``"ok"``, ``"missing"``,
        or ``"mismatch"``.
    """
    if client is None:
        client = InspireClient()

    results: list[CheckResult] = []

    for i, entry in enumerate(entries, start=1):
        if verbose:
            print(f"[{i}/{len(entries)}] Checking {entry.key} …")

        record = client.lookup_by_texkey(entry.key)

        if record is None:
            results.append(
                CheckResult(
                    key=entry.key,
                    status="missing",
                    local_entry={"key": entry.key, "type": entry.entry_type, **entry.fields},
                )
            )
            continue

        mismatches = _compare_fields(entry, record, client)

        results.append(
            CheckResult(
                key=entry.key,
                status="mismatch" if mismatches else "ok",
                mismatches=mismatches,
                local_entry={"key": entry.key, "type": entry.entry_type, **entry.fields},
                inspire_record=record,
            )
        )

    return results

"""Step 1: check bib entries against InspireHEP.

Entries not found by texkey are flagged as ``"missing"``.
Entries where key fields differ are flagged as ``"mismatch"``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Any

from .cache import CheckCache
from .inspire import InspireClient
from .models import BibEntry, CheckResult, FieldMismatch

if TYPE_CHECKING:
    from .ads import AdsClient

_ADS_BIBCODE_RE = re.compile(r"/abs/([^/\s]+?)/?$")
_ENSUREMATH_RE = re.compile(r"\\ensuremath\{([^{}]*)\}")
_LATEX_CMD_RE = re.compile(r"\\([A-Za-z]+)")

# Unicode Greek letters mapped to their LaTeX command names so that
# e.g. γ and \gamma both normalise to "gamma" before comparison.
# InspireHEP's JSON API returns Unicode while BibTeX exports use \gamma etc.
_UNICODE_TO_LATEX_NAME: dict[str, str] = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta",
    "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta",
    "Ε": "epsilon", "Ζ": "zeta", "Η": "eta", "Θ": "theta",
    "Ι": "iota", "Κ": "kappa", "Λ": "lambda", "Μ": "mu",
    "Ν": "nu", "Ξ": "xi", "Ο": "omicron", "Π": "pi",
    "Ρ": "rho", "Σ": "sigma", "Τ": "tau", "Υ": "upsilon",
    "Φ": "phi", "Χ": "chi", "Ψ": "psi", "Ω": "omega",
}

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


def _extract_ads_bibcode(adsurl: str) -> str | None:
    """Extract the ADS bibcode from an adsurl field value, or return None."""
    m = _ADS_BIBCODE_RE.search(adsurl)
    return m.group(1) if m else None


def _normalise(value: str) -> str:
    """Normalise a field value for comparison.

    Handles LaTeX ↔ Unicode equivalences so that e.g.
    ``{\\ensuremath{\\gamma}}`` and ``γ`` both reduce to ``gamma``.
    """
    # Map Unicode Greek letters to their LaTeX command names first.
    for char, name in _UNICODE_TO_LATEX_NAME.items():
        value = value.replace(char, name)
    # Strip \ensuremath{...} wrappers, keeping inner content.
    while _ENSUREMATH_RE.search(value):
        value = _ENSUREMATH_RE.sub(r"\1", value)
    # Replace remaining \command sequences with the bare command name.
    value = _LATEX_CMD_RE.sub(r"\1", value)
    # Strip braces left over from LaTeX grouping.
    value = value.replace("{", "").replace("}", "")
    # Standard: drop combining accents, lowercase, collapse whitespace.
    value = unicodedata.normalize("NFD", value)
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    return " ".join(value.lower().split())


def _compare_fields(
    entry: BibEntry,
    record: dict[str, Any],
    client: InspireClient,
) -> list[FieldMismatch]:
    """Compare selected fields of *entry* against an InspireHEP *record*."""
    mismatches: list[FieldMismatch] = []
    for local_field, extractor in _COMPARED_FIELDS:
        local_val = _normalise(entry.fields.get(local_field, ""))
        inspire_val = _normalise(getattr(InspireClient, extractor)(record))
        if local_val and inspire_val and local_val != inspire_val:
            mismatches.append(
                FieldMismatch(
                    field_name=local_field,
                    local_value=entry.fields.get(local_field, ""),
                    remote_value=getattr(InspireClient, extractor)(record),
                )
            )
    return mismatches


def _compare_fields_ads(
    entry: BibEntry,
    doc: dict[str, Any],
) -> list[FieldMismatch]:
    """Compare selected fields of *entry* against an ADS *doc*."""
    from .ads import AdsClient

    mismatches: list[FieldMismatch] = []
    for local_field, extractor in _COMPARED_FIELDS:
        local_val = _normalise(entry.fields.get(local_field, ""))
        ads_val = _normalise(getattr(AdsClient, extractor)(doc))
        if local_val and ads_val and local_val != ads_val:
            mismatches.append(
                FieldMismatch(
                    field_name=local_field,
                    local_value=entry.fields.get(local_field, ""),
                    remote_value=getattr(AdsClient, extractor)(doc),
                )
            )
    return mismatches


def _entry_from_result(result: CheckResult) -> BibEntry:
    """Reconstruct a BibEntry from the local_entry dict stored in a CheckResult."""
    local_e = result.local_entry or {}
    return BibEntry(
        key=local_e.get("key", result.key),
        entry_type=local_e.get("type", ""),
        fields={k: v for k, v in local_e.items() if k not in ("key", "type")},
    )


def check_entries(
    entries: list[BibEntry],
    client: InspireClient | None = None,
    ads_client: AdsClient | None = None,
    verbose: bool = False,
    batch_size: int = 50,
    cache: CheckCache | None = None,
    ignore_keys: set[str] | None = None,
) -> list[CheckResult]:
    """Check *entries* against InspireHEP and return one result per entry.

    Entries are looked up in batches (OR queries) to minimise the number of
    API requests.  Already-cached results are reused without hitting the API.
    Keys in *ignore_keys* are silently skipped.

    For entries that remain ``"missing"`` after the InspireHEP pass, a two-tier
    fallback is attempted when the local entry has an ``adsurl`` field:

    1. InspireHEP is queried by the ADS bibcode embedded in the ``adsurl``
       (``external_system_identifiers.value``).  On a hit the status becomes
       ``"found_via_ads"``.
    2. If *ads_client* is provided and tier 1 still finds nothing, the ADS API
       is queried directly.  On a hit with matching fields the status becomes
       ``"ok_via_ads"``; with differing fields it becomes ``"mismatch_via_ads"``.

    Parameters
    ----------
    entries : list[BibEntry]
        Entries to check, typically parsed from a .bib file.
    client : InspireClient, optional
        InspireHEP API client. A default client is created when ``None``.
    ads_client : AdsClient, optional
        NASA ADS API client.  When ``None`` the ADS direct fallback is skipped.
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
        One result per non-ignored input entry.
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

    # Fallback for "missing" entries that have an adsurl field.
    # Tier 1: look up the bibcode on InspireHEP (no extra credentials needed).
    # Tier 2: query ADS directly (requires ads_client with a valid token).
    for result in results:
        if result.status != "missing":
            continue
        adsurl = (result.local_entry or {}).get("adsurl", "")
        bibcode = _extract_ads_bibcode(adsurl)
        if not bibcode:
            continue

        # Tier 1 — InspireHEP via ADS bibcode
        if verbose:
            print(f"  Trying ADS bibcode {bibcode!r} for {result.key!r} …")
        inspire_record = client.lookup_by_ads_bibcode(bibcode)
        if inspire_record is not None:
            temp = _entry_from_result(result)
            result.status = "found_via_ads"
            result.inspire_record = inspire_record
            result.mismatches = _compare_fields(temp, inspire_record, client)
            continue

        # Tier 2 — ADS directly
        if ads_client is None:
            continue
        if verbose:
            print(f"  Querying ADS directly for {bibcode!r} …")
        ads_doc = ads_client.lookup_by_bibcode(bibcode)
        if ads_doc is None:
            continue
        temp = _entry_from_result(result)
        ads_mismatches = _compare_fields_ads(temp, ads_doc)
        result.ads_record = ads_doc
        result.status = "ok_via_ads" if not ads_mismatches else "mismatch_via_ads"
        result.mismatches = ads_mismatches

    if cache is not None:
        cache.save()

    return results

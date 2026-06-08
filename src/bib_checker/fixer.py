"""Apply InspireHEP canonical field values to a .bib file (fix mismatches).

Reads the mismatch results produced by Step 1 and rewrites the affected
fields in the original .bib file with the InspireHEP values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import bibtexparser
from bibtexparser.model import Field

from .inspire import InspireClient

# Fields the fixer is allowed to update (in order of preference).
# Users can restrict this list via the --fields CLI option.
DEFAULT_FIX_FIELDS: list[str] = ["doi", "eprint", "year", "title"]


def _canonical_values(
    result: dict[str, Any],
    fields: list[str],
) -> dict[str, str]:
    """Extract InspireHEP canonical values for *fields* from a result dict.

    Parameters
    ----------
    result : dict[str, Any]
        A single entry from ``results.json`` (output of Step 1).
    fields : list[str]
        Field names to extract.

    Returns
    -------
    updates : dict[str, str]
        Mapping of field name → InspireHEP canonical value.
        Only fields that are both in *fields* and have a non-empty InspireHEP
        value are included.
    """
    record = result.get("inspire_record") or {}
    updates: dict[str, str] = {}

    extractor_map = {
        "doi": InspireClient.get_doi,
        "eprint": InspireClient.get_eprint,
        "year": InspireClient.get_year,
        "title": InspireClient.get_title,
    }

    for f in fields:
        extractor = extractor_map.get(f)
        if extractor is None:
            continue
        value = extractor(record)
        if value:
            updates[f] = value

    return updates


def apply_fixes(
    bib_path: str | Path,
    results: list[dict[str, Any]],
    output_path: str | Path | None = None,
    fields: list[str] | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Rewrite mismatch entries in *bib_path* with InspireHEP canonical values.

    Only entries with ``status == "mismatch"`` that have an ``inspire_record``
    are modified.  Entries with ``status == "missing"`` are left untouched
    (we don't know which record to fix them to).

    Parameters
    ----------
    bib_path : str or Path
        Original ``.bib`` file to read.
    results : list[dict[str, Any]]
        Parsed contents of ``results.json`` produced by Step 1.
    output_path : str or Path, optional
        Where to write the fixed bib.  Defaults to *bib_path* (in-place).
        When *dry_run* is ``True`` nothing is written regardless.
    fields : list[str], optional
        Restrict which fields are updated.  Defaults to
        :data:`DEFAULT_FIX_FIELDS`.
    dry_run : bool, optional
        When ``True``, compute changes but do not write anything.

    Returns
    -------
    applied : list[dict[str, Any]]
        One entry per modified citation key::

            {"key": str, "field": str, "old": str, "new": str}

    Raises
    ------
    FileNotFoundError
        Raised if *bib_path* does not exist.
    """
    bib_path = Path(bib_path)
    if not bib_path.exists():
        raise FileNotFoundError(f"Bib file not found: {bib_path}")

    if fields is None:
        fields = DEFAULT_FIX_FIELDS

    if output_path is None:
        output_path = bib_path
    output_path = Path(output_path)

    # Build a map of key → canonical updates for mismatch entries only.
    fix_map: dict[str, dict[str, str]] = {}
    for r in results:
        if r.get("status") != "mismatch":
            continue
        updates = _canonical_values(r, fields)
        if updates:
            fix_map[r["key"]] = updates

    library = bibtexparser.parse_file(str(bib_path))

    applied: list[dict[str, Any]] = []

    for entry in library.entries:
        updates = fix_map.get(entry.key)
        if not updates:
            continue

        current = {f.key: f.value for f in entry.fields}
        for field_name, new_value in updates.items():
            old_value = current.get(field_name, "")
            if old_value == new_value:
                continue
            applied.append(
                {"key": entry.key, "field": field_name, "old": old_value, "new": new_value}
            )
            if not dry_run:
                entry.set_field(Field(field_name, new_value))

    if not dry_run:
        output_path.write_text(bibtexparser.write_string(library), encoding="utf-8")

    return applied

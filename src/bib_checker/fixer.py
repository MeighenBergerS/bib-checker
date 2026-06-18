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
from .parser import write_reformatted_bib

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
) -> tuple[list[dict[str, Any]], set[str]]:
    """Rewrite mismatch entries in *bib_path* with InspireHEP canonical values.

    Only entries with ``status == "mismatch"`` that have an ``inspire_record``
    are modified.  Entries with ``status == "missing"`` are left untouched
    (we don't know which record to fix them to).

    The output file is written with clean entries first and still-flagged
    entries (missing + mismatches with no fixable InspireHEP record) moved
    to the end, separated by a comment block.

    Parameters
    ----------
    bib_path : str or Path
        Original ``.bib`` file to read.
    results : list[dict[str, Any]]
        Parsed contents of ``results.json`` produced by Step 1.
    output_path : str or Path, optional
        Where to write the fixed bib.  Defaults to a new file named
        ``<stem>_fixed.bib`` next to *bib_path*.
        When *dry_run* is ``True`` nothing is written regardless.
    fields : list[str], optional
        Restrict which fields are updated.  Defaults to
        :data:`DEFAULT_FIX_FIELDS`.
    dry_run : bool, optional
        When ``True``, compute changes but do not write anything.

    Returns
    -------
    applied : list[dict[str, Any]]
        One entry per modified field::

            {"key": str, "field": str, "old": str, "new": str}

    still_flagged : set[str]
        Citation keys that still need manual attention after the fix
        (missing entries + mismatches with no fixable InspireHEP record).

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
        output_path = bib_path.with_name(bib_path.stem + "_fixed" + bib_path.suffix)
    output_path = Path(output_path)

    # Build a map of key → canonical updates for mismatch entries only.
    fix_map: dict[str, dict[str, str]] = {}
    for r in results:
        if r.get("status") != "mismatch":
            continue
        updates = _canonical_values(r, fields)
        if updates:
            fix_map[r["key"]] = updates

    # Keys that remain problematic after the fix pass:
    # - all missing entries (no record to fix to)
    # - mismatch entries where we found no fixable canonical values
    still_flagged: set[str] = set()
    for r in results:
        key = r["key"]
        if r.get("status") == "missing" or key not in fix_map:
            still_flagged.add(key)

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
        # Write a patched intermediate file, then reformat to move
        # still-flagged entries to the end with a separator comment.
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(bibtexparser.write_string(library))
            tmp_path = Path(tmp.name)

        try:
            write_reformatted_bib(tmp_path, still_flagged, output_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    return applied, still_flagged

"""Parse a .bib file into BibEntry objects using bibtexparser v2."""

from __future__ import annotations

from pathlib import Path

import bibtexparser

from .models import BibEntry

_SEPARATOR = """\
% ##########################################################################
% These citations need validation/checking
% ##########################################################################
"""


def _unwrap_braces(value: str) -> str:
    """Strip a single layer of surrounding braces if present."""
    s = value.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    return s


def _field_to_str(value: object) -> str:
    """Convert a bibtexparser field value to a plain string."""
    # bibtexparser v2 fields_dict returns Field objects; extract the .value.
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, str):
        return _unwrap_braces(value)
    # NameList: join back as "Last, First and Last, First"
    if hasattr(value, "__iter__") and not isinstance(value, (bytes, bytearray)):
        parts: list[str] = []
        for person in value:
            if hasattr(person, "merge_str"):
                parts.append(person.merge_str)
            else:
                parts.append(str(person))
        return " and ".join(parts)
    return str(value)


def parse_bib_file(path: str | Path) -> list[BibEntry]:
    """Parse a .bib file and return a list of BibEntry objects.

    Parameters
    ----------
    path : str or Path
        Path to the .bib file to parse.

    Returns
    -------
    entries : list[BibEntry]
        Parsed entries in document order.

    Raises
    ------
    FileNotFoundError
        Raised if *path* does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Bib file not found: {path}")

    library = bibtexparser.parse_file(str(path))

    entries: list[BibEntry] = []
    for entry in library.entries:
        fields: dict[str, str] = {k: _field_to_str(v) for k, v in entry.fields_dict.items()}
        entries.append(
            BibEntry(
                key=entry.key,
                entry_type=entry.entry_type,
                fields=fields,
            )
        )

    return entries


def write_reformatted_bib(
    source_path: str | Path,
    flagged_keys: set[str],
    output_path: str | Path,
) -> tuple[int, int]:
    """Write a reformatted .bib file with flagged entries moved to the end.

    OK entries are written first, followed by a separator comment block, then
    the flagged (missing/mismatch) entries.  If there are no flagged entries
    the separator is omitted and the file is a straight copy.

    Parameters
    ----------
    source_path : str or Path
        Original .bib file to read from.
    flagged_keys : set[str]
        Citation keys that need attention (missing or mismatch).
    output_path : str or Path
        Path to write the reformatted .bib file to.

    Returns
    -------
    n_ok : int
        Number of entries written before the separator.
    n_flagged : int
        Number of entries written after the separator.

    Raises
    ------
    FileNotFoundError
        Raised if *source_path* does not exist.
    """
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.exists():
        raise FileNotFoundError(f"Bib file not found: {source_path}")

    library = bibtexparser.parse_file(str(source_path))

    ok_entries = [e for e in library.entries if e.key not in flagged_keys]
    bad_entries = [e for e in library.entries if e.key in flagged_keys]

    ok_lib = bibtexparser.Library()
    ok_lib.add(ok_entries)

    ok_text = bibtexparser.write_string(ok_lib).rstrip("\n")

    if bad_entries:
        bad_lib = bibtexparser.Library()
        bad_lib.add(bad_entries)
        bad_text = bibtexparser.write_string(bad_lib)
        full_text = ok_text + "\n\n" + _SEPARATOR + "\n" + bad_text
    else:
        full_text = ok_text + "\n"

    output_path.write_text(full_text, encoding="utf-8")

    return len(ok_entries), len(bad_entries)

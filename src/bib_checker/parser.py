"""Parse a .bib file into BibEntry objects using bibtexparser v2."""

from __future__ import annotations

from pathlib import Path

import bibtexparser
from bibtexparser.middlewares.names import SeparateCoAuthors, MergeCoAuthors
from bibtexparser.middlewares.latex_encoding import LatexDecodingMiddleware

from .models import BibEntry


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
        fields: dict[str, str] = {
            k: _field_to_str(v) for k, v in entry.fields_dict.items()
        }
        entries.append(
            BibEntry(
                key=entry.key,
                entry_type=entry.entry_type,
                fields=fields,
            )
        )

    return entries

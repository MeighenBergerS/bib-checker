"""Data models for bib-checker (plain dataclasses, no external deps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BibEntry:
    """A single entry parsed from a .bib file.

    Attributes
    ----------
    key : str
        Citation key, e.g. ``Spolyar:2007qv``.
    entry_type : str
        BibTeX entry type, e.g. ``article`` or ``preprint``.
    fields : dict[str, str]
        Raw field values keyed by field name.
    """

    key: str
    entry_type: str  # article, preprint, inproceedings, …
    fields: dict[str, str] = field(default_factory=dict)

    # Convenience accessors for commonly compared fields.
    @property
    def title(self) -> str:
        """Title field value, or an empty string if absent."""
        return self.fields.get("title", "")

    @property
    def doi(self) -> str:
        """DOI field value, or an empty string if absent."""
        return self.fields.get("doi", "")

    @property
    def eprint(self) -> str:
        """ArXiv eprint field value, or an empty string if absent."""
        return self.fields.get("eprint", "")

    @property
    def year(self) -> str:
        """Year field value, or an empty string if absent."""
        return self.fields.get("year", "")

    @property
    def authors(self) -> list[str]:
        """List of author strings split on " and "."""
        raw = self.fields.get("author", "")
        return [a.strip() for a in raw.split(" and ") if a.strip()]


@dataclass
class FieldMismatch:
    """A single field difference between a local bib entry and InspireHEP.

    Attributes
    ----------
    field_name : str
        Name of the differing field, e.g. ``doi`` or ``year``.
    local_value : str
        The value found in the local .bib file.
    inspire_value : str
        The value returned by InspireHEP.
    """

    field_name: str
    local_value: str
    inspire_value: str


@dataclass
class CheckResult:
    """The result of checking one BibEntry against InspireHEP.

    Attributes
    ----------
    key : str
        Citation key of the checked entry.
    status : str
        Outcome: ``"ok"``, ``"missing"``, or ``"mismatch"``.
    mismatches : list[FieldMismatch]
        Fields that differ from the InspireHEP record. Empty when
        status is not ``"mismatch"``.
    local_entry : dict[str, Any] or None
        Flat dict representation of the local bib entry.
    inspire_record : dict[str, Any] or None
        Raw API record from InspireHEP, or ``None`` when missing.
    """

    key: str
    status: str  # "ok" | "missing" | "mismatch"
    mismatches: list[FieldMismatch] = field(default_factory=list)
    local_entry: dict[str, Any] | None = None
    inspire_record: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result to a JSON-compatible dict."""
        return {
            "key": self.key,
            "status": self.status,
            "mismatches": [
                {
                    "field": m.field_name,
                    "local": m.local_value,
                    "inspire": m.inspire_value,
                }
                for m in self.mismatches
            ],
            "local_entry": self.local_entry,
            "inspire_record": self.inspire_record,
        }


@dataclass
class Suggestion:
    """A candidate InspireHEP record suggested for a missing or mismatched entry.

    Attributes
    ----------
    for_key : str
        Citation key from the original bib file this suggestion targets.
    texkey : str
        InspireHEP texkey of the candidate record.
    title : str
        Title of the candidate record.
    authors : list[str]
        Author full names from InspireHEP.
    year : str
        Publication year.
    doi : str
        DOI of the candidate record.
    eprint : str
        ArXiv eprint identifier.
    inspire_id : str
        InspireHEP internal record ID.
    """

    for_key: str
    texkey: str
    title: str
    authors: list[str]
    year: str
    doi: str
    eprint: str
    inspire_id: str

    def to_dict(self) -> dict[str, Any]:
        """Serialise the suggestion to a JSON-compatible dict."""
        return {
            "for_key": self.for_key,
            "texkey": self.texkey,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "eprint": self.eprint,
            "inspire_id": self.inspire_id,
        }

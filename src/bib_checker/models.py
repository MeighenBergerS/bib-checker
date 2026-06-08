"""Data models (plain dataclasses, no external deps)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BibEntry:
    """Represents a single entry parsed from a .bib file."""

    key: str
    entry_type: str  # article, preprint, inproceedings, …
    fields: dict[str, str] = field(default_factory=dict)

    # Convenience accessors for commonly compared fields.
    @property
    def title(self) -> str:
        return self.fields.get("title", "")

    @property
    def doi(self) -> str:
        return self.fields.get("doi", "")

    @property
    def eprint(self) -> str:
        return self.fields.get("eprint", "")

    @property
    def year(self) -> str:
        return self.fields.get("year", "")

    @property
    def authors(self) -> list[str]:
        raw = self.fields.get("author", "")
        return [a.strip() for a in raw.split(" and ") if a.strip()]


@dataclass
class FieldMismatch:
    """Records a single field difference between local bib and InspireHEP."""

    field_name: str
    local_value: str
    inspire_value: str


@dataclass
class CheckResult:
    """Result of checking one BibEntry against InspireHEP."""

    key: str
    status: str  # "ok" | "missing" | "mismatch"
    mismatches: list[FieldMismatch] = field(default_factory=list)
    local_entry: dict[str, Any] | None = None
    inspire_record: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
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
    """A candidate InspireHEP record suggested for a missing/mismatched entry."""

    for_key: str
    texkey: str
    title: str
    authors: list[str]
    year: str
    doi: str
    eprint: str
    inspire_id: str

    def to_dict(self) -> dict[str, Any]:
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

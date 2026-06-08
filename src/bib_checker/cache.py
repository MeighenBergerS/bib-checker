"""On-disk JSON cache for InspireHEP lookup results.

Caches CheckResult objects keyed by texkey.  Each cached entry stores a
short hash of the local bib entry's fields; if the local entry changes the
cached result is treated as stale and discarded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import CheckResult, FieldMismatch

_CACHE_VERSION = 2


def _entry_hash(fields: dict[str, str]) -> str:
    """Return a 16-hex-char SHA-256 digest of *fields* for staleness detection.

    Parameters
    ----------
    fields : dict[str, str]
        Field dict from a :class:`~bib_checker.models.BibEntry`.

    Returns
    -------
    digest : str
        16-character hex string.
    """
    canonical = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _result_from_dict(raw: dict[str, Any]) -> CheckResult:
    """Deserialise a :class:`~bib_checker.models.CheckResult` from a dict.

    Parameters
    ----------
    raw : dict[str, Any]
        Dict as produced by :meth:`~bib_checker.models.CheckResult.to_dict`.

    Returns
    -------
    result : CheckResult
        Reconstructed dataclass instance.
    """
    return CheckResult(
        key=raw["key"],
        status=raw["status"],
        nonstandard_key=raw.get("nonstandard_key", False),
        mismatches=[
            FieldMismatch(
                field_name=m["field"],
                local_value=m["local"],
                # support both old "inspire" key and new "remote" key
                remote_value=m.get("remote") or m.get("inspire", ""),
            )
            for m in raw.get("mismatches", [])
        ],
        local_entry=raw.get("local_entry"),
        inspire_record=raw.get("inspire_record"),
        ads_record=raw.get("ads_record"),
    )


class CheckCache:
    """Persistent on-disk cache mapping texkey → :class:`~bib_checker.models.CheckResult`.

    Parameters
    ----------
    path : str or Path
        Path to the JSON cache file.  The file is created on first
        :meth:`save`.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: dict[str, Any] = {}
        self._dirty = False
        self._load()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load cache from disk, silently ignoring corrupt files."""
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if raw.get("version") == _CACHE_VERSION:
                self._data = raw.get("entries", {})
        except (json.JSONDecodeError, KeyError, OSError):
            self._data = {}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, texkey: str, entry_fields: dict[str, str]) -> CheckResult | None:
        """Return a cached result if the local entry hasn't changed, else ``None``.

        Parameters
        ----------
        texkey : str
            Citation key to look up.
        entry_fields : dict[str, str]
            Current field values from the local bib entry.

        Returns
        -------
        result : CheckResult or None
            Cached result, or ``None`` if not cached or stale.
        """
        slot = self._data.get(texkey)
        if slot is None:
            return None
        if slot.get("entry_hash") != _entry_hash(entry_fields):
            return None
        return _result_from_dict(slot["result"])

    def put(self, texkey: str, entry_fields: dict[str, str], result: CheckResult) -> None:
        """Store a result in the in-memory cache.

        Parameters
        ----------
        texkey : str
            Citation key.
        entry_fields : dict[str, str]
            Field values of the local bib entry at check time.
        result : CheckResult
            The result to cache.
        """
        self._data[texkey] = {
            "entry_hash": _entry_hash(entry_fields),
            "result": result.to_dict(),
        }
        self._dirty = True

    def save(self) -> None:
        """Write the cache to disk (only when entries have been added/updated)."""
        if not self._dirty:
            return
        payload = {"version": _CACHE_VERSION, "entries": self._data}
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        self._dirty = False

    @staticmethod
    def default_path(bib_path: str | Path) -> Path:
        """Return the default cache file path next to *bib_path*.

        Parameters
        ----------
        bib_path : str or Path
            Path to the ``.bib`` file being checked.

        Returns
        -------
        path : Path
            A hidden file named ``.{stem}-cache.json`` in the same directory.
        """
        bib = Path(bib_path)
        return bib.with_name(f".{bib.stem}-cache.json")

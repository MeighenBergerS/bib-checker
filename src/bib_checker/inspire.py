"""InspireHEP REST API v1 client.

Docs: https://inspirehep.net/api
"""

from __future__ import annotations

import time
from typing import Any

import requests

_BASE = "https://inspirehep.net/api"
_DEFAULT_TIMEOUT = 15  # seconds per request
_RATE_LIMIT_DELAY = 0.5  # seconds between requests


class InspireClient:
    """Thin wrapper around the InspireHEP literature API."""

    def __init__(
        self,
        timeout: float = _DEFAULT_TIMEOUT,
        rate_limit_delay: float = _RATE_LIMIT_DELAY,
    ) -> None:
        self._timeout = timeout
        self._delay = rate_limit_delay
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "bib-checker/0.1 (https://github.com/MeighenBergerS/bib-checker)"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def lookup_by_texkey(self, texkey: str) -> dict[str, Any] | None:
        """Return the first InspireHEP record matching *texkey*, or None."""
        params = {
            "q": f"texkey:{texkey}",
            "fields": "texkeys,titles,authors,dois,arxiv_eprints,publication_info,imprint",
            "size": 1,
        }
        data = self._get(f"{_BASE}/literature", params=params)
        hits = data.get("hits", {}).get("hits", [])
        return hits[0] if hits else None

    def search(
        self,
        query: str,
        size: int = 5,
    ) -> list[dict[str, Any]]:
        """Free-text search; returns up to *size* records."""
        params = {
            "q": query,
            "fields": "texkeys,titles,authors,dois,arxiv_eprints,publication_info",
            "size": size,
            "sort": "mostrecent",
        }
        data = self._get(f"{_BASE}/literature", params=params)
        return data.get("hits", {}).get("hits", [])

    # ------------------------------------------------------------------
    # Helpers to extract normalised values from raw API records
    # ------------------------------------------------------------------

    @staticmethod
    def get_texkey(record: dict[str, Any]) -> str:
        keys = record.get("metadata", {}).get("texkeys", [])
        return keys[0] if keys else ""

    @staticmethod
    def get_title(record: dict[str, Any]) -> str:
        titles = record.get("metadata", {}).get("titles", [])
        return titles[0].get("title", "") if titles else ""

    @staticmethod
    def get_doi(record: dict[str, Any]) -> str:
        dois = record.get("metadata", {}).get("dois", [])
        return dois[0].get("value", "") if dois else ""

    @staticmethod
    def get_eprint(record: dict[str, Any]) -> str:
        eprints = record.get("metadata", {}).get("arxiv_eprints", [])
        return eprints[0].get("value", "") if eprints else ""

    @staticmethod
    def get_year(record: dict[str, Any]) -> str:
        pub = record.get("metadata", {}).get("publication_info", [])
        if pub:
            return str(pub[0].get("year", ""))
        imprint = record.get("metadata", {}).get("imprint", [])
        if imprint:
            return str(imprint[0].get("date", ""))[:4]
        return ""

    @staticmethod
    def get_authors(record: dict[str, Any]) -> list[str]:
        authors = record.get("metadata", {}).get("authors", [])
        return [a.get("full_name", "") for a in authors]

    @staticmethod
    def get_inspire_id(record: dict[str, Any]) -> str:
        return str(record.get("id", ""))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        time.sleep(self._delay)
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

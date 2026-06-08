"""InspireHEP REST API v1 client.

Notes
-----
API documentation: https://inspirehep.net/api
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
        """Create a new client.

        Parameters
        ----------
        timeout : float, optional
            Per-request timeout in seconds. Default is 15.
        rate_limit_delay : float, optional
            Seconds to wait between consecutive requests. Default is 0.5.
        """
        self._timeout = timeout
        self._delay = rate_limit_delay
        self._session = requests.Session()
        self._session.headers["User-Agent"] = (
            "bib-checker/0.1 (https://github.com/MeighenBergerS/bib-checker)"
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def lookup_by_texkey(self, texkey: str) -> dict[str, Any] | None:
        """Return the first InspireHEP record matching *texkey*, or None.

        Parameters
        ----------
        texkey : str
            InspireHEP texkey, e.g. ``Spolyar:2007qv``.

        Returns
        -------
        record : dict[str, Any] or None
            Raw API hit dict, or ``None`` if no record was found.
        """
        results = self.lookup_by_texkeys([texkey])
        return results.get(texkey)

    def lookup_by_texkeys(
        self,
        texkeys: list[str],
        batch_size: int = 50,
    ) -> dict[str, dict[str, Any]]:
        """Fetch multiple records in batches using OR queries.

        Parameters
        ----------
        texkeys : list[str]
            Citation keys to look up.
        batch_size : int, optional
            Maximum number of keys per API request. Default is 50.

        Returns
        -------
        records : dict[str, dict[str, Any]]
            Mapping of texkey to the matching raw API hit dict.
            Keys not found on InspireHEP are absent from the result.
        """
        records: dict[str, dict[str, Any]] = {}
        for i in range(0, len(texkeys), batch_size):
            chunk = texkeys[i : i + batch_size]
            query = " or ".join(f"texkey:{k}" for k in chunk)
            params = {
                "q": query,
                "fields": "texkeys,titles,authors,dois,arxiv_eprints,publication_info,imprint",
                "size": batch_size,
            }
            data = self._get(f"{_BASE}/literature", params=params)
            for hit in data.get("hits", {}).get("hits", []):
                key = self.get_texkey(hit)
                if key:
                    records[key] = hit
        return records

    def search(
        self,
        query: str,
        size: int = 5,
    ) -> list[dict[str, Any]]:
        """Search InspireHEP and return up to *size* records.

        Parameters
        ----------
        query : str
            Free-text InspireHEP search query.
        size : int, optional
            Maximum number of results to return. Default is 5.

        Returns
        -------
        hits : list[dict[str, Any]]
            Raw API hit dicts ordered by most-recent.
        """
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
        """Extract the primary texkey from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        texkey : str
            Primary texkey, or an empty string if absent.
        """
        keys = record.get("metadata", {}).get("texkeys", [])
        return keys[0] if keys else ""

    @staticmethod
    def get_title(record: dict[str, Any]) -> str:
        """Extract the primary title from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        title : str
            Primary title string, or an empty string if absent.
        """
        titles = record.get("metadata", {}).get("titles", [])
        return titles[0].get("title", "") if titles else ""

    @staticmethod
    def get_doi(record: dict[str, Any]) -> str:
        """Extract the primary DOI from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        doi : str
            Primary DOI string, or an empty string if absent.
        """
        dois = record.get("metadata", {}).get("dois", [])
        return dois[0].get("value", "") if dois else ""

    @staticmethod
    def get_eprint(record: dict[str, Any]) -> str:
        """Extract the primary ArXiv eprint ID from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        eprint : str
            ArXiv eprint identifier, or an empty string if absent.
        """
        eprints = record.get("metadata", {}).get("arxiv_eprints", [])
        return eprints[0].get("value", "") if eprints else ""

    @staticmethod
    def get_year(record: dict[str, Any]) -> str:
        """Extract the publication year from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        year : str
            Four-digit year string, or an empty string if absent.
        """
        pub = record.get("metadata", {}).get("publication_info", [])
        if pub:
            return str(pub[0].get("year", ""))
        imprint = record.get("metadata", {}).get("imprint", [])
        if imprint:
            return str(imprint[0].get("date", ""))[:4]
        return ""

    @staticmethod
    def get_authors(record: dict[str, Any]) -> list[str]:
        """Extract author full names from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        authors : list[str]
            Full name strings for each author.
        """
        authors = record.get("metadata", {}).get("authors", [])
        return [a.get("full_name", "") for a in authors]

    @staticmethod
    def get_inspire_id(record: dict[str, Any]) -> str:
        """Extract the InspireHEP internal record ID from a raw API record.

        Parameters
        ----------
        record : dict[str, Any]
            Raw API hit dict.

        Returns
        -------
        inspire_id : str
            Record ID as a string, or an empty string if absent.
        """
        return str(record.get("id", ""))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a GET request and return the parsed JSON response.

        Parameters
        ----------
        url : str
            Request URL.
        params : dict[str, Any]
            Query parameters.

        Returns
        -------
        data : dict[str, Any]
            Parsed JSON response body.
        """
        time.sleep(self._delay)
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

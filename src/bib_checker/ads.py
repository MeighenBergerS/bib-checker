"""NASA ADS REST API client for bib-checker."""

from __future__ import annotations

import time
from typing import Any

import requests

_BASE = "https://api.adsabs.harvard.edu/v1"
_DEFAULT_TIMEOUT = 15
_RATE_LIMIT_DELAY = 0.5


class AdsClient:
    """Thin wrapper around the NASA ADS search API."""

    def __init__(
        self,
        token: str,
        timeout: float = _DEFAULT_TIMEOUT,
        rate_limit_delay: float = _RATE_LIMIT_DELAY,
    ) -> None:
        self._timeout = timeout
        self._delay = rate_limit_delay
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "bib-checker/0.1 (https://github.com/MeighenBergerS/bib-checker)",
                "Authorization": f"Bearer {token}",
            }
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def lookup_by_bibcode(self, bibcode: str) -> dict[str, Any] | None:
        """Return the ADS document matching *bibcode*, or None.

        Parameters
        ----------
        bibcode : str
            ADS bibcode, e.g. ``2019ApJS..243...10P``.

        Returns
        -------
        doc : dict[str, Any] or None
            Raw ADS document dict, or ``None`` if not found.
        """
        params = {
            "q": f'bibcode:"{bibcode}"',
            "fl": "bibcode,title,author,year,doi,identifier",
            "rows": 1,
        }
        data = self._get(f"{_BASE}/search/query", params)
        docs = data.get("response", {}).get("docs", [])
        return docs[0] if docs else None

    # ------------------------------------------------------------------
    # Helpers to extract normalised values from raw ADS documents
    # ------------------------------------------------------------------

    @staticmethod
    def get_title(doc: dict[str, Any]) -> str:
        titles = doc.get("title") or []
        return titles[0] if titles else ""

    @staticmethod
    def get_year(doc: dict[str, Any]) -> str:
        return str(doc.get("year", ""))

    @staticmethod
    def get_doi(doc: dict[str, Any]) -> str:
        dois = doc.get("doi") or []
        return dois[0] if dois else ""

    @staticmethod
    def get_eprint(doc: dict[str, Any]) -> str:
        for ident in doc.get("identifier", []):
            if ident.startswith("arXiv:"):
                return ident[6:]
        return ""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        time.sleep(self._delay)
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        return response.json()

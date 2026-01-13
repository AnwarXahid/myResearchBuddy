from __future__ import annotations

from typing import Any, Dict

import httpx


class CitationVerifier:
    def verify(self, title: str) -> Dict[str, Any]:
        result = {
            "title": title,
            "status": "unverified",
            "identifiers": {},
            "bibtex": "",
        }
        if not title.strip():
            return result
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    "https://api.crossref.org/works",
                    params={"query.title": title, "rows": 1},
                )
                resp.raise_for_status()
                data = resp.json()
            items = data.get("message", {}).get("items", [])
            if not items:
                return result
            item = items[0]
            doi = item.get("DOI")
            if doi:
                result["status"] = "verified"
                result["identifiers"] = {"doi": doi}
                result["bibtex"] = self._fetch_bibtex(doi)
        except httpx.HTTPError:
            return result
        return result

    def _fetch_bibtex(self, doi: str) -> str:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex"
                )
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPError:
            return ""

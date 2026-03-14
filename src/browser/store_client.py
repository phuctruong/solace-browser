# Diagram: 01-triangle-architecture
from __future__ import annotations

from typing import Any

import requests


class StoreClient:
    def __init__(self, base_url: str, api_key: str, oauth3_scopes: str = "store.contribute") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.oauth3_scopes = oauth3_scopes

    def _headers(self, write: bool = False) -> dict[str, str]:
        out = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if write:
            out["Content-Type"] = "application/json"
            out["X-OAuth3-Scopes"] = self.oauth3_scopes
        return out

    def upload_primewiki(self, site: str, wiki_data: dict[str, Any]) -> dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/store/primewiki/{site}",
            json=wiki_data,
            headers=self._headers(write=True),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def upload_snapshot(self, site: str, page: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/store/snapshots/{site}/{page}",
            json=snapshot,
            headers=self._headers(write=True),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def upload_recipe(self, recipe: dict[str, Any]) -> dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/store/recipes",
            json=recipe,
            headers=self._headers(write=True),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def download_primewiki(self, site: str) -> dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/store/primewiki/{site}",
            headers=self._headers(write=False),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def download_recipes(self, site: str) -> dict[str, Any]:
        r = requests.get(
            f"{self.base_url}/store/recipes/{site}",
            headers=self._headers(write=False),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

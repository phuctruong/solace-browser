"""Stillwater Store HTTP client for Phase 3 integration."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional

import requests


DEFAULT_BASE_URL = "https://solaceagi.com/store/api/v1"


class StoreError(RuntimeError):
    """Raised when store API operations fail."""


@dataclass(frozen=True)
class StoreRecipe:
    recipe_id: str
    version: str
    channel: str
    recipe_ir: Dict[str, Any]
    rung_verified: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recipe_id": self.recipe_id,
            "version": self.version,
            "channel": self.channel,
            "recipe_ir": dict(self.recipe_ir),
            "rung_verified": int(self.rung_verified),
        }


class StillwaterStoreClient:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout_seconds: int = 15,
        retries: int = 3,
        session: Any | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = int(timeout_seconds)
        self.retries = int(retries)
        self.session = session or requests.Session()

    def list_recipes(self, channel: str = "stable") -> List[Dict[str, Any]]:
        payload = self._request_json("GET", "/store/recipes", params={"channel": channel})
        rows = payload.get("recipes")
        if not isinstance(rows, list):
            raise StoreError("invalid response: missing recipes list")
        return rows

    def fetch_recipe(self, recipe_id: str, version: str = "latest") -> Dict[str, Any]:
        recipe_id = recipe_id.strip()
        if not recipe_id:
            raise StoreError("recipe_id is required")

        if version == "latest":
            latest_doc = self._request_json("GET", f"/store/recipes/{recipe_id}")
            if "recipe_ir" in latest_doc and "version" in latest_doc:
                return {
                    "recipe_id": str(latest_doc.get("recipe_id", recipe_id)),
                    "version": str(latest_doc["version"]),
                    "channel": str(latest_doc.get("channel", "stable")),
                    "recipe_ir": dict(latest_doc["recipe_ir"]),
                    "rung_verified": int(latest_doc.get("rung_verified", 0)),
                }

            versions = latest_doc.get("versions")
            if not isinstance(versions, list) or not versions:
                raise StoreError("invalid response: latest recipe missing version metadata")
            resolved = self._choose_latest_version(versions)
            version = resolved

        version_doc = self._request_json("GET", f"/store/recipes/{recipe_id}/v/{version}")
        if "recipe_ir" not in version_doc:
            raise StoreError("invalid response: missing recipe_ir")

        return {
            "recipe_id": str(version_doc.get("recipe_id", recipe_id)),
            "version": str(version_doc.get("version", version)),
            "channel": str(version_doc.get("channel", "stable")),
            "recipe_ir": dict(version_doc["recipe_ir"]),
            "rung_verified": int(version_doc.get("rung_verified", 0)),
        }

    def post_metrics(self, recipe_id: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        recipe_id = recipe_id.strip()
        if not recipe_id:
            raise StoreError("recipe_id is required")
        if not isinstance(metrics, dict):
            raise StoreError("metrics payload must be an object")

        payload = self._request_json("POST", f"/store/recipes/{recipe_id}/metrics", json=metrics)
        if str(payload.get("status", "")) != "recorded":
            raise StoreError(f"store metrics not recorded: {payload}")
        return payload

    def _request_json(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        last_error: Optional[Exception] = None
        url = f"{self.base_url}{path}"

        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.retries:
                    raise StoreError(f"store request failed after {self.retries} attempts: {exc}") from exc
                time.sleep(0.05 * attempt)
                continue

            if response.status_code >= 500:
                last_error = StoreError(f"store server error {response.status_code}: {response.text}")
                if attempt >= self.retries:
                    raise last_error
                time.sleep(0.05 * attempt)
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise StoreError(f"store request failed: {response.status_code} {response.text}") from exc

            try:
                payload = response.json()
            except ValueError as exc:
                raise StoreError("store response is not valid JSON") from exc

            if not isinstance(payload, dict):
                raise StoreError("store response must be a JSON object")
            return payload

        if last_error is not None:
            raise StoreError(str(last_error)) from last_error
        raise StoreError("store request failed")

    @staticmethod
    def _choose_latest_version(versions: List[Dict[str, Any]]) -> str:
        def semver_key(value: str) -> tuple[int, int, int, str]:
            raw = value.strip()
            parts = raw.split(".")
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
                return (int(parts[0]), int(parts[1]), int(parts[2]), raw)
            return (0, 0, 0, raw)

        candidates = [str(v.get("version", "")) for v in versions if str(v.get("version", "")).strip()]
        if not candidates:
            raise StoreError("cannot resolve latest version: empty versions")
        return sorted(candidates, key=semver_key, reverse=True)[0]

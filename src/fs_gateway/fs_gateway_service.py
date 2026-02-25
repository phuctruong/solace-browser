"""Filesystem gateway service with OAuth3 scope gates.

Scope model:
- fs.read: read file contents
- fs.write: write file contents
- fs.list: list directory entries
- fs.hash: hash file content + metadata
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from oauth3.vault import OAuth3Vault

GENESIS_HASH = "0" * 64


class FSAccessError(RuntimeError):
    """Base filesystem gateway error."""


class FSScopeError(FSAccessError):
    """Raised when OAuth3 scope gate blocks an operation."""


class FSPathError(FSAccessError):
    """Raised when path escapes the configured workspace root."""


class FilesystemGatewayService:
    """Local fs-gateway read/write/list/hash service."""

    def __init__(
        self,
        *,
        vault: OAuth3Vault,
        workspace_root: Path | str,
        proof_log: Path | str | None = None,
    ) -> None:
        self.vault = vault
        self.workspace_root = Path(workspace_root).expanduser().resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        if proof_log is None:
            proof_log = Path("scratch") / "evidence" / "phase_1.5" / "fs_gateway_proof.jsonl"
        self.proof_log = Path(proof_log)
        self.proof_log.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = self._load_tail_hash()

    def read(self, path: str, scope_token: str) -> Dict[str, Any]:
        target = self._resolve_user_path(path)
        self._require_scope(scope_token, "fs.read", op="read", path=path)

        if not target.exists() or not target.is_file():
            raise FSPathError(f"read target does not exist: {path}")

        content = target.read_text(encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result = {
            "path": self._rel(target),
            "content": content,
            "hash": digest,
            "size": len(content.encode("utf-8")),
        }
        self._log_event("FS_READ", {"path": result["path"], "hash": digest, "size": result["size"]})
        return result

    def write(self, path: str, content: str, scope_token: str) -> Dict[str, Any]:
        target = self._resolve_user_path(path)
        self._require_scope(scope_token, "fs.write", op="write", path=path)

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        size = len(content.encode("utf-8"))
        result = {"path": self._rel(target), "hash": digest, "size": size}
        self._log_event("FS_WRITE", result)
        return result

    def list(self, path: str, scope_token: str) -> Dict[str, List[str]]:
        target = self._resolve_user_path(path)
        self._require_scope(scope_token, "fs.list", op="list", path=path)

        if not target.exists() or not target.is_dir():
            raise FSPathError(f"list target is not a directory: {path}")

        entries = sorted([p.name for p in target.iterdir()])
        result = {"path": self._rel(target), "files": entries}
        self._log_event("FS_LIST", {"path": result["path"], "count": len(entries)})
        return result

    def hash(self, path: str, scope_token: str) -> Dict[str, Any]:
        target = self._resolve_user_path(path)
        self._require_scope(scope_token, "fs.hash", op="hash", path=path)

        if not target.exists() or not target.is_file():
            raise FSPathError(f"hash target does not exist: {path}")

        raw = target.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        mtime = int(target.stat().st_mtime)
        result = {"path": self._rel(target), "hash": digest, "modified_at": mtime}
        self._log_event("FS_HASH", result)
        return result

    def _require_scope(self, token_id: str, required_scope: str, *, op: str, path: str) -> None:
        allowed = self.vault.validate_token(token_id, required_scope)
        if not allowed:
            self._log_event(
                "FS_SCOPE_DENIED",
                {
                    "operation": op,
                    "path": path,
                    "required_scope": required_scope,
                    "token_id": token_id,
                },
            )
            raise FSScopeError(
                f"scope denied for {op}: required={required_scope} path={path}"
            )

    def _resolve_user_path(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.workspace_root / candidate).resolve()

        root = self.workspace_root
        if resolved != root and root not in resolved.parents:
            raise FSPathError(
                f"path outside workspace root: {path} (allowed root: {root})"
            )
        return resolved

    def _rel(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.workspace_root))
        except ValueError as exc:
            raise FSPathError(f"cannot relativize path {path}: {exc}") from exc

    def _log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        event = {
            "event_type": event_type,
            "prev_hash": self._prev_hash,
            "data": data,
        }
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        event["event_hash"] = event_hash

        with self.proof_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        self._prev_hash = event_hash

    def _load_tail_hash(self) -> str:
        if not self.proof_log.exists():
            return GENESIS_HASH

        last_nonempty = ""
        with self.proof_log.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_nonempty = line

        if not last_nonempty:
            return GENESIS_HASH

        payload = json.loads(last_nonempty)
        return str(payload.get("event_hash") or GENESIS_HASH)

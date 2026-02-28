"""
OAuth3-gated local file system access layer.

Every public function enforces scope gates (G1-G4) before touching the
filesystem.  Operations are restricted to the current user's permissions;
no privilege escalation is performed.

Safety rules enforced here:
  - machine.read.home scope: access limited to Path.home() subtree
  - machine.read.files scope: unrestricted path access (within user perms)
  - Path traversal protection: resolved path must remain inside allowed root
  - Symlink escape protection: resolved symlink target must stay in allowed root
  - Binary file guard: binary files return metadata only, no content
  - Maximum file read size: MAX_READ_BYTES (default 1 MB)
  - Secret-path blocklist: .ssh/, .gnupg/, .aws/credentials, raw .env files
  - Write and delete operations require high-risk step-up nonce

Audit logging: every operation emits a structured audit record to
~/.stillwater/machine_audit.jsonl (created if absent, fails silently).

Rung: 274177 (file system access — medium irreversibility)
"""

from __future__ import annotations

import datetime
import fnmatch
import json
import logging
import mimetypes
import os
import stat
import time
from pathlib import Path
from typing import List, Optional

from src.oauth3.token import AgencyToken
from src.oauth3.enforcement import ScopeGate
from src.machine.scopes import (
    SCOPE_READ_FILES,
    SCOPE_READ_HOME,
    SCOPE_LIST_DIRECTORY,
    SCOPE_WRITE_FILES,
    SCOPE_DELETE_FILES,
)


# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

MAX_READ_BYTES: int = 1_000_000          # 1 MB
MAX_SEARCH_RESULTS: int = 500            # cap on search hits
AUDIT_LOG_PATH: Path = Path.home() / ".stillwater" / "machine_audit.jsonl"
logger = logging.getLogger(__name__)

# Paths that are NEVER accessible, regardless of scope.
# These are matched against the resolved absolute path (as a string).
_SECRET_PATH_PATTERNS: tuple = (
    "/.ssh/",
    "/.gnupg/",
    "/.aws/credentials",
    "/.aws/config",
    # Any file whose name is exactly .env or ends with .env (e.g. .env.local)
    # Checked separately by _is_secret_path()
)

_SECRET_BASENAME_PATTERNS: tuple = (
    ".env",
    ".env.*",
    "id_rsa",
    "id_ecdsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _audit(action: str, token: AgencyToken, path: str, extra: Optional[dict] = None) -> None:
    """Emit a structured audit record. Fails silently to not block operations."""
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": _now_iso(),
            "action": action,
            "token_id": token.token_id,
            "subject": token.subject,
            "path": _redact_path(path),
            **(extra or {}),
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        logger.warning("machine file audit write failed for %s: %s", path, exc)


def _redact_path(path: str) -> str:
    """Redact secret-adjacent paths before logging."""
    if _is_secret_path(path):
        return "<REDACTED_SECRET_PATH>"
    return path


def _is_secret_path(path: str) -> bool:
    """
    Return True if the path matches any secret-path pattern.

    Checks both directory patterns (e.g. /.ssh/) and filename patterns
    (e.g. .env, *.pem).
    """
    norm = str(path)

    # Directory patterns
    for pat in _SECRET_PATH_PATTERNS:
        if pat in norm:
            return True

    # Basename patterns
    basename = os.path.basename(norm)
    for pat in _SECRET_BASENAME_PATTERNS:
        if fnmatch.fnmatch(basename, pat):
            return True

    return False


def _resolve_safe(path: str, allowed_root: Optional[Path]) -> tuple:
    """
    Resolve path and enforce directory confinement.

    Returns:
        (resolved: Path, error: str | None)
        If error is not None, the operation must be rejected.

    Checks:
      1. Path must be resolvable (no broken references for existing checks).
      2. Resolved path must be inside allowed_root (if provided).
      3. If the path is a symlink, its resolved target must also be inside
         allowed_root (symlink escape protection).
      4. Secret-path check applied to resolved path string.
    """
    try:
        p = Path(path)
        # For non-existent paths (write targets), resolve parent
        if not p.exists():
            resolved = p.parent.resolve() / p.name
        else:
            resolved = p.resolve()
    except (OSError, ValueError) as exc:
        return None, f"path_resolution_error: {exc}"

    # Symlink escape: if original path is a symlink, verify resolved target
    try:
        if Path(path).is_symlink():
            link_target = Path(path).resolve()
            if allowed_root and not _is_within(link_target, allowed_root):
                return None, (
                    f"symlink_escape: symlink at {path!r} resolves to "
                    f"{link_target!r} which is outside allowed root {allowed_root!r}"
                )
    except OSError as exc:
        logger.debug("Symlink inspection failed for %s: %s", path, exc)

    if allowed_root and not _is_within(resolved, allowed_root):
        return None, (
            f"path_traversal: resolved path {resolved!r} is outside "
            f"allowed root {allowed_root!r}"
        )

    if _is_secret_path(str(resolved)):
        return None, f"secret_path_blocked: {_redact_path(str(resolved))}"

    return resolved, None


def _is_within(child: Path, parent: Path) -> bool:
    """Return True if child is inside parent (inclusive of parent itself)."""
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _allowed_root_for_scopes(token: AgencyToken) -> Optional[Path]:
    """
    Determine the allowed root directory based on granted scopes.

    Rules:
      - machine.read.files → no root restriction (user fs access)
      - machine.read.home only → restrict to Path.home()
      - Neither → None (caller must have already failed the gate check)
    """
    if SCOPE_READ_FILES in token.scopes:
        return None  # unrestricted (within user perms)
    if SCOPE_READ_HOME in token.scopes:
        return Path.home().resolve()
    return Path.home().resolve()  # default to home as safest fallback


def _is_binary(path: Path) -> bool:
    """
    Heuristic: return True if file appears to be binary.

    Reads the first 8 KB and checks for null bytes.
    """
    try:
        with open(path, "rb") as fh:
            chunk = fh.read(8192)
        return b"\x00" in chunk
    except OSError:
        return False


def _file_info(p: Path) -> dict:
    """Return metadata dict for a path (does not read content)."""
    try:
        s = p.stat()
        return {
            "path": str(p),
            "name": p.name,
            "is_dir": p.is_dir(),
            "is_file": p.is_file(),
            "is_symlink": p.is_symlink(),
            "size_bytes": s.st_size,
            "modified": datetime.datetime.fromtimestamp(
                s.st_mtime, tz=datetime.timezone.utc
            ).isoformat(),
            "permissions": oct(stat.S_IMODE(s.st_mode)),
        }
    except OSError as exc:
        return {"path": str(p), "error": str(exc)}


def _gate_check(token: AgencyToken, required_scopes: list) -> Optional[dict]:
    """
    Run ScopeGate.check_all() for the given scopes.

    Returns None if allowed, or an error dict if blocked.
    """
    gate = ScopeGate(token=token, required_scopes=required_scopes)
    result = gate.check_all()
    if not result.allowed:
        return {
            "error": result.error_code,
            "detail": result.error_detail,
            "blocking_gate": result.blocking_gate,
            "missing_scopes": result.missing_scopes,
        }
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_directory(path: str, token: AgencyToken) -> dict:
    """
    List the contents of a directory.

    Required scopes: machine.list.directory OR machine.read.files
    (either scope is accepted — list is less sensitive than read).

    Args:
        path:  Absolute or relative directory path.
        token: AgencyToken with at least one of the required scopes.

    Returns:
        {
          "path": str,
          "entries": [{"path", "name", "is_dir", "is_file", "size_bytes",
                        "modified", "permissions"}, ...],
          "count": int,
        }
        or {"error": ..., "detail": ...} on failure.
    """
    # Scope check: accept machine.list.directory OR machine.read.files
    has_list = SCOPE_LIST_DIRECTORY in token.scopes
    has_read = SCOPE_READ_FILES in token.scopes
    has_home = SCOPE_READ_HOME in token.scopes

    if not (has_list or has_read or has_home):
        gate_err = _gate_check(token, [SCOPE_LIST_DIRECTORY])
        return gate_err or {
            "error": "OAUTH3_SCOPE_DENIED",
            "detail": f"Requires {SCOPE_LIST_DIRECTORY} or {SCOPE_READ_FILES}",
        }

    # Validate token validity (expiry + revocation)
    gate = ScopeGate(token=token, required_scopes=[SCOPE_LIST_DIRECTORY])
    g1 = gate.g1_schema()
    g2 = gate.g2_expiry()
    g4 = gate.g4_revocation()
    for gr in (g1, g2, g4):
        if not gr.passed:
            return {"error": gr.error_code, "detail": gr.error_detail}

    allowed_root = _allowed_root_for_scopes(token)
    resolved, err = _resolve_safe(path, allowed_root)
    if err:
        return {"error": "ACCESS_DENIED", "detail": err}

    if not resolved.exists():
        return {"error": "NOT_FOUND", "detail": f"Path does not exist: {path!r}"}

    if not resolved.is_dir():
        return {"error": "NOT_A_DIRECTORY", "detail": f"Path is not a directory: {path!r}"}

    try:
        entries = [_file_info(child) for child in sorted(resolved.iterdir())]
    except PermissionError as exc:
        return {"error": "PERMISSION_DENIED", "detail": str(exc)}

    _audit("list_directory", token, str(resolved))
    return {
        "path": str(resolved),
        "entries": entries,
        "count": len(entries),
    }


def read_file(
    path: str,
    token: AgencyToken,
    max_bytes: int = MAX_READ_BYTES,
) -> dict:
    """
    Read the content of a text file.

    Required scope: machine.read.files OR machine.read.home
    Binary files: returns metadata only (no content).
    Maximum size: max_bytes (default 1 MB). Larger files return an error.

    Args:
        path:      Absolute or relative file path.
        token:     AgencyToken with machine.read.files or machine.read.home scope.
        max_bytes: Maximum bytes to read (default 1 MB).

    Returns:
        {
          "path": str,
          "content": str,
          "size_bytes": int,
          "modified": str (ISO 8601),
          "encoding": str,
          "binary": bool,
        }
        or {"error": ..., "detail": ...} on failure.
    """
    has_read = SCOPE_READ_FILES in token.scopes
    has_home = SCOPE_READ_HOME in token.scopes

    if not (has_read or has_home):
        return _gate_check(token, [SCOPE_READ_FILES]) or {
            "error": "OAUTH3_SCOPE_DENIED",
            "detail": f"Requires {SCOPE_READ_FILES} or {SCOPE_READ_HOME}",
        }

    gate = ScopeGate(token=token, required_scopes=[SCOPE_READ_FILES if has_read else SCOPE_READ_HOME])
    g1 = gate.g1_schema()
    g2 = gate.g2_expiry()
    g4 = gate.g4_revocation()
    for gr in (g1, g2, g4):
        if not gr.passed:
            return {"error": gr.error_code, "detail": gr.error_detail}

    allowed_root = _allowed_root_for_scopes(token)
    resolved, err = _resolve_safe(path, allowed_root)
    if err:
        return {"error": "ACCESS_DENIED", "detail": err}

    if not resolved.exists():
        return {"error": "NOT_FOUND", "detail": f"File does not exist: {path!r}"}

    if not resolved.is_file():
        return {"error": "NOT_A_FILE", "detail": f"Path is not a regular file: {path!r}"}

    try:
        file_size = resolved.stat().st_size
        modified = datetime.datetime.fromtimestamp(
            resolved.stat().st_mtime, tz=datetime.timezone.utc
        ).isoformat()
    except OSError as exc:
        return {"error": "STAT_ERROR", "detail": str(exc)}

    if file_size > max_bytes:
        return {
            "error": "FILE_TOO_LARGE",
            "detail": (
                f"File size {file_size} bytes exceeds limit {max_bytes} bytes. "
                "Use max_bytes parameter or request a smaller file."
            ),
            "size_bytes": file_size,
        }

    if _is_binary(resolved):
        _audit("read_file_binary_skipped", token, str(resolved))
        return {
            "path": str(resolved),
            "binary": True,
            "content": None,
            "size_bytes": file_size,
            "modified": modified,
            "encoding": "binary",
        }

    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except PermissionError as exc:
        return {"error": "PERMISSION_DENIED", "detail": str(exc)}
    except OSError as exc:
        return {"error": "READ_ERROR", "detail": str(exc)}

    _audit("read_file", token, str(resolved), {"size_bytes": file_size})
    return {
        "path": str(resolved),
        "content": content,
        "size_bytes": file_size,
        "modified": modified,
        "encoding": "utf-8",
        "binary": False,
    }


def write_file(path: str, content: str, token: AgencyToken) -> dict:
    """
    Write (create or overwrite) a text file.

    Required scope: machine.write.files (HIGH RISK — step-up required)

    Args:
        path:    Absolute or relative file path.
        content: Text content to write.
        token:   AgencyToken with machine.write.files scope.

    Returns:
        {
          "path": str,
          "size_bytes": int,
          "written": true,
        }
        or {"error": ..., "detail": ...} on failure.
    """
    err = _gate_check(token, [SCOPE_WRITE_FILES])
    if err:
        return err

    allowed_root = _allowed_root_for_scopes(token)
    resolved, path_err = _resolve_safe(path, allowed_root)
    if path_err:
        return {"error": "ACCESS_DENIED", "detail": path_err}

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        size = resolved.stat().st_size
    except PermissionError as exc:
        return {"error": "PERMISSION_DENIED", "detail": str(exc)}
    except OSError as exc:
        return {"error": "WRITE_ERROR", "detail": str(exc)}

    _audit("write_file", token, str(resolved), {"size_bytes": size})
    return {
        "path": str(resolved),
        "size_bytes": size,
        "written": True,
    }


def delete_path(path: str, token: AgencyToken) -> dict:
    """
    Delete a file or empty directory.

    Required scope: machine.delete.files (HIGH RISK — step-up required)

    Directories must be empty; non-empty directory deletion is rejected to
    prevent accidental recursive removal.

    Args:
        path:  Absolute or relative path to delete.
        token: AgencyToken with machine.delete.files scope.

    Returns:
        {
          "path": str,
          "deleted": true,
          "kind": "file" | "directory",
        }
        or {"error": ..., "detail": ...} on failure.
    """
    err = _gate_check(token, [SCOPE_DELETE_FILES])
    if err:
        return err

    allowed_root = _allowed_root_for_scopes(token)
    resolved, path_err = _resolve_safe(path, allowed_root)
    if path_err:
        return {"error": "ACCESS_DENIED", "detail": path_err}

    if not resolved.exists():
        return {"error": "NOT_FOUND", "detail": f"Path does not exist: {path!r}"}

    try:
        if resolved.is_dir():
            # Reject non-empty directories
            children = list(resolved.iterdir())
            if children:
                return {
                    "error": "DIRECTORY_NOT_EMPTY",
                    "detail": (
                        f"Directory {resolved!r} has {len(children)} entries. "
                        "Delete contents first."
                    ),
                }
            resolved.rmdir()
            kind = "directory"
        else:
            resolved.unlink()
            kind = "file"
    except PermissionError as exc:
        return {"error": "PERMISSION_DENIED", "detail": str(exc)}
    except OSError as exc:
        return {"error": "DELETE_ERROR", "detail": str(exc)}

    _audit("delete_path", token, str(resolved), {"kind": kind})
    return {
        "path": str(resolved),
        "deleted": True,
        "kind": kind,
    }


def search_files(
    directory: str,
    pattern: str,
    token: AgencyToken,
) -> list:
    """
    Search for files matching a glob pattern within a directory.

    Required scope: machine.read.files

    Args:
        directory: Root directory to search from.
        pattern:   Glob pattern (e.g. '*.py', '**/*.json').
        token:     AgencyToken with machine.read.files scope.

    Returns:
        List of file-info dicts (same schema as list_directory entries).
        Returns [{"error": ..., "detail": ...}] on failure.
    """
    has_read = SCOPE_READ_FILES in token.scopes
    has_home = SCOPE_READ_HOME in token.scopes

    if not (has_read or has_home):
        return [_gate_check(token, [SCOPE_READ_FILES]) or {
            "error": "OAUTH3_SCOPE_DENIED",
            "detail": f"Requires {SCOPE_READ_FILES} or {SCOPE_READ_HOME}",
        }]

    gate = ScopeGate(token=token, required_scopes=[SCOPE_READ_FILES if has_read else SCOPE_READ_HOME])
    g1 = gate.g1_schema()
    g2 = gate.g2_expiry()
    g4 = gate.g4_revocation()
    for gr in (g1, g2, g4):
        if not gr.passed:
            return [{"error": gr.error_code, "detail": gr.error_detail}]

    allowed_root = _allowed_root_for_scopes(token)
    resolved_dir, err = _resolve_safe(directory, allowed_root)
    if err:
        return [{"error": "ACCESS_DENIED", "detail": err}]

    if not resolved_dir.exists() or not resolved_dir.is_dir():
        return [{"error": "NOT_A_DIRECTORY", "detail": f"Not a directory: {directory!r}"}]

    results: List[dict] = []
    try:
        for match in resolved_dir.glob(pattern):
            if len(results) >= MAX_SEARCH_RESULTS:
                break
            if _is_secret_path(str(match)):
                continue
            if allowed_root and not _is_within(match.resolve(), allowed_root):
                continue
            results.append(_file_info(match))
    except (OSError, PermissionError) as exc:
        logger.debug("File search stopped early in %s: %s", resolved_dir, exc)

    _audit("search_files", token, str(resolved_dir), {"pattern": pattern, "hits": len(results)})
    return results


def get_file_info(path: str, token: AgencyToken) -> dict:
    """
    Return metadata for a file or directory without reading content.

    Required scope: machine.list.directory (or machine.read.files)

    Args:
        path:  Absolute or relative path.
        token: AgencyToken with machine.list.directory scope.

    Returns:
        File-info dict (path, name, is_dir, is_file, size_bytes, modified,
        permissions) or {"error": ..., "detail": ...} on failure.
    """
    has_list = SCOPE_LIST_DIRECTORY in token.scopes
    has_read = SCOPE_READ_FILES in token.scopes
    has_home = SCOPE_READ_HOME in token.scopes

    if not (has_list or has_read or has_home):
        return _gate_check(token, [SCOPE_LIST_DIRECTORY]) or {
            "error": "OAUTH3_SCOPE_DENIED",
            "detail": f"Requires {SCOPE_LIST_DIRECTORY} or {SCOPE_READ_FILES}",
        }

    gate = ScopeGate(token=token, required_scopes=[SCOPE_LIST_DIRECTORY])
    g1 = gate.g1_schema()
    g2 = gate.g2_expiry()
    g4 = gate.g4_revocation()
    for gr in (g1, g2, g4):
        if not gr.passed:
            return {"error": gr.error_code, "detail": gr.error_detail}

    allowed_root = _allowed_root_for_scopes(token)
    resolved, err = _resolve_safe(path, allowed_root)
    if err:
        return {"error": "ACCESS_DENIED", "detail": err}

    if not resolved.exists():
        return {"error": "NOT_FOUND", "detail": f"Path does not exist: {path!r}"}

    _audit("get_file_info", token, str(resolved))
    return _file_info(resolved)

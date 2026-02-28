"""
FastAPI router for machine access endpoints.

Runs as part of the local solace-browser HTTP server.
All endpoints require:
  1. Bearer token in Authorization header (AgencyToken JSON or token_id lookup)
  2. OAuth3 scope enforcement via ScopeGate (G1-G4 gates)

Endpoint summary:
  GET    /machine/files          — list directory (machine.list.directory)
  GET    /machine/files/read     — read file content (machine.read.files)
  POST   /machine/files/write    — write file (machine.write.files)
  DELETE /machine/files          — delete file/dir (machine.delete.files)
  POST   /machine/terminal/execute — execute command (machine.execute.command)
  POST   /machine/terminal/safe  — safe command (machine.execute.safe)
  GET    /machine/system         — system info (machine.read.sysinfo)
  GET    /machine/processes      — process list (machine.read.processes)
  POST   /machine/tunnel/start   — start tunnel (machine.tunnel.manage)
  POST   /machine/tunnel/stop    — stop tunnel (machine.tunnel.manage)
  GET    /machine/tunnel/status  — tunnel status (machine.tunnel.manage)

Security model:
  - Fail-closed: any token parse error → 401
  - Missing scope → 403 with OAUTH3_SCOPE_DENIED
  - Operation errors → 400 or 500 with structured error body
  - No exception details leaked to client for unexpected errors (500)

Rung: 274177
"""

from __future__ import annotations

import json
import traceback
from typing import Optional

try:
    from fastapi import APIRouter, Depends, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

from src.oauth3.token import AgencyToken
from src.machine import (
    file_browser,
    terminal as terminal_mod,
)
from src.machine.tunnel import TunnelConfig, TunnelServer
from src.machine.scopes import (
    SCOPE_LIST_DIRECTORY,
    SCOPE_READ_FILES,
    SCOPE_WRITE_FILES,
    SCOPE_DELETE_FILES,
    SCOPE_EXECUTE_COMMAND,
    SCOPE_EXECUTE_SAFE,
    SCOPE_READ_SYSINFO,
    SCOPE_READ_PROCESSES,
    SCOPE_TUNNEL_MANAGE,
)

if not _FASTAPI_AVAILABLE:
    # Provide a stub so the module can be imported in test environments
    # without FastAPI installed.
    class _StubRouter:
        def get(self, *a, **kw):
            return lambda f: f
        def post(self, *a, **kw):
            return lambda f: f
        def delete(self, *a, **kw):
            return lambda f: f

    router = _StubRouter()
else:
    router = APIRouter(prefix="/machine", tags=["machine"])


# ---------------------------------------------------------------------------
# Shared tunnel server instance (module-level singleton)
# ---------------------------------------------------------------------------

_tunnel_server = TunnelServer()


# ---------------------------------------------------------------------------
# Pydantic request models (only defined if FastAPI is available)
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:
    class WriteFileRequest(BaseModel):
        path: str
        content: str

    class ExecuteCommandRequest(BaseModel):
        command: str
        timeout: int = 30
        cwd: Optional[str] = None

    class SafeCommandRequest(BaseModel):
        command: str

    class TunnelStartRequest(BaseModel):
        local_port: int
        remote_host: str = "tunnel.solaceagi.com"
        auth_token: str = ""


# ---------------------------------------------------------------------------
# Token extraction helper
# ---------------------------------------------------------------------------

def _extract_token(authorization: Optional[str]) -> AgencyToken:
    """
    Parse AgencyToken from Authorization: Bearer <json> header.

    The Bearer value is expected to be a URL-safe base64-encoded or raw JSON
    serialization of the AgencyToken dict.

    For simplicity in v0.1, we accept raw JSON directly.
    In production, this would look up a token_id from a TokenStore.

    Raises:
        HTTPException(401): if header is missing or token fails to parse.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "MISSING_AUTH",
                "detail": "Authorization: Bearer <token_json> header required.",
            },
        )

    raw = authorization[len("Bearer "):]
    try:
        data = json.loads(raw)
        token = AgencyToken.from_dict(data)
        return token
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "INVALID_TOKEN",
                "detail": f"Failed to parse Bearer token: {exc}",
            },
        )


def _error_response(result: dict) -> JSONResponse:
    """
    Convert an operation error dict to an appropriate HTTP response.

    Maps OAuth3 error codes to HTTP status codes.
    """
    error = result.get("error", "UNKNOWN_ERROR")

    status_map = {
        "OAUTH3_SCOPE_DENIED": 403,
        "OAUTH3_TOKEN_EXPIRED": 401,
        "OAUTH3_TOKEN_REVOKED": 401,
        "OAUTH3_MALFORMED_TOKEN": 401,
        "ACCESS_DENIED": 403,
        "PATH_TRAVERSAL": 403,
        "SECRET_PATH_BLOCKED": 403,
        "COMMAND_BLOCKED": 403,
        "COMMAND_NOT_ALLOWED": 403,
        "NOT_FOUND": 404,
        "NOT_A_FILE": 400,
        "NOT_A_DIRECTORY": 400,
        "DIRECTORY_NOT_EMPTY": 400,
        "FILE_TOO_LARGE": 413,
        "INVALID_PORT": 400,
        "TUNNEL_ALREADY_RUNNING": 409,
        "PERMISSION_DENIED": 403,
        "COMMAND_TIMEOUT": 408,
    }

    status = status_map.get(error, 500)
    return JSONResponse(status_code=status, content=result)


def _has_error(result) -> bool:
    """Return True if result dict contains an error key."""
    if isinstance(result, dict) and "error" in result:
        return True
    if isinstance(result, list) and result and isinstance(result[0], dict) and "error" in result[0]:
        return True
    return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

if _FASTAPI_AVAILABLE:

    @router.get("/files")
    async def list_directory(
        path: str = ".",
        authorization: Optional[str] = Header(default=None),
    ):
        """
        List directory contents.

        Scope: machine.list.directory (or machine.read.files / machine.read.home)
        """
        token = _extract_token(authorization)
        result = file_browser.list_directory(path=path, token=token)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.get("/files/read")
    async def read_file(
        path: str,
        max_bytes: int = 1_000_000,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Read file content.

        Scope: machine.read.files (or machine.read.home)
        """
        token = _extract_token(authorization)
        result = file_browser.read_file(path=path, token=token, max_bytes=max_bytes)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.post("/files/write")
    async def write_file(
        body: WriteFileRequest,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Write (create or overwrite) a file.

        Scope: machine.write.files (HIGH RISK)
        """
        token = _extract_token(authorization)
        result = file_browser.write_file(
            path=body.path,
            content=body.content,
            token=token,
        )
        if _has_error(result):
            return _error_response(result)
        return result

    @router.delete("/files")
    async def delete_file(
        path: str,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Delete a file or empty directory.

        Scope: machine.delete.files (HIGH RISK)
        """
        token = _extract_token(authorization)
        result = file_browser.delete_path(path=path, token=token)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.post("/terminal/execute")
    async def execute_command(
        body: ExecuteCommandRequest,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Execute an arbitrary shell command.

        Scope: machine.execute.command (HIGH RISK)
        """
        token = _extract_token(authorization)
        result = terminal_mod.execute_command(
            command=body.command,
            token=token,
            timeout=body.timeout,
            cwd=body.cwd,
        )
        if _has_error(result):
            return _error_response(result)
        return result

    @router.post("/terminal/safe")
    async def execute_safe(
        body: SafeCommandRequest,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Execute a read-only command from the allowlist.

        Scope: machine.execute.safe
        """
        token = _extract_token(authorization)
        result = terminal_mod.execute_safe(
            command=body.command,
            token=token,
        )
        if _has_error(result):
            return _error_response(result)
        return result

    @router.get("/system")
    async def get_system_info(
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Return system information.

        Scope: machine.read.sysinfo
        """
        token = _extract_token(authorization)
        result = terminal_mod.get_system_info(token=token)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.get("/processes")
    async def list_processes(
        authorization: Optional[str] = Header(default=None),
    ):
        """
        List running processes (top 50 by CPU).

        Scope: machine.read.processes
        """
        token = _extract_token(authorization)
        result = terminal_mod.list_processes(token=token)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.post("/tunnel/start")
    async def tunnel_start(
        body: TunnelStartRequest,
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Start a reverse tunnel to solaceagi.com.

        Scope: machine.tunnel.manage (HIGH RISK — exposes local machine)
        """
        token = _extract_token(authorization)
        config = TunnelConfig(
            local_port=body.local_port,
            remote_host=body.remote_host,
            auth_token=body.auth_token,
        )
        result = _tunnel_server.start(config=config, token=token)
        if _has_error(result):
            return _error_response(result)
        return result

    @router.post("/tunnel/stop")
    async def tunnel_stop(
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Stop the active reverse tunnel.

        Scope: machine.tunnel.manage
        """
        token = _extract_token(authorization)
        result = _tunnel_server.stop(token=token)
        if isinstance(result, dict) and _has_error(result):
            return _error_response(result)
        return {"stopped": bool(result)}

    @router.get("/tunnel/status")
    async def tunnel_status(
        authorization: Optional[str] = Header(default=None),
    ):
        """
        Return current tunnel status.

        Scope: machine.tunnel.manage
        """
        token = _extract_token(authorization)
        result = _tunnel_server.status(token=token)
        if _has_error(result):
            return _error_response(result)
        return result

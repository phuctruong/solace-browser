# Diagram: 01-triangle-architecture
"""
Auth Proxy — 3-Layer Defense for Chromium CDP Access

Layer 1: Auth Proxy (port 8888) — validates Bearer tokens on every request
Layer 2: Hidden Chromium CDP (port 9225) — localhost only, never exposed
Layer 3: Session token exchange — short-lived session tokens for WebSocket

Design:
- FAIL-CLOSED: Missing/invalid token -> 401 immediately
- NO token extension: Expired -> 401, no silent renewal
- NO plaintext on disk: Tokens in memory only
- NO fallback: Import errors or config issues -> refuse to start

Reference: Diagram 09 (OAuth3 Auth Proxy — 3-Layer Defense)
Rung: 641
"""

from __future__ import annotations

import hashlib
import http.client
import json
import logging
import re
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

logger = logging.getLogger("auth_proxy")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TOKEN_PREFIX = "sw_sk_"
SESSION_TOKEN_PREFIX = "st_sess_"
SESSION_TOKEN_TTL_SECONDS = 300  # 5 minutes
DEFAULT_PROXY_PORT = 8888
DEFAULT_CDP_PORT = 9225
DEFAULT_BIND_HOST = "127.0.0.1"

# Minimum token length after prefix (reject trivially short tokens)
MIN_TOKEN_SUFFIX_LENGTH = 8

# Token format regex: sw_sk_ followed by alphanumeric + underscore/hyphen, min 8 chars
_TOKEN_FORMAT_RE = re.compile(r"^sw_sk_[A-Za-z0-9_\-]{8,}$")

# JSON error responses
_UNAUTHORIZED_BODY = json.dumps({
    "error": "unauthorized",
    "message": "Missing or invalid Bearer token",
    "redirect": "https://www.solaceagi.com/auth/login",
}).encode("utf-8")

_EXPIRED_BODY = json.dumps({
    "error": "token_expired",
    "message": "Token has expired. Re-authenticate to continue.",
    "redirect": "https://www.solaceagi.com/auth/login",
}).encode("utf-8")

_REVOKED_BODY = json.dumps({
    "error": "token_revoked",
    "message": "Token has been revoked.",
    "redirect": "https://www.solaceagi.com/auth/login",
}).encode("utf-8")

_FORBIDDEN_BODY = json.dumps({
    "error": "forbidden",
    "message": "External connections to CDP port are forbidden.",
}).encode("utf-8")


# ---------------------------------------------------------------------------
# TokenInfo — in-memory token metadata (never stores plaintext token)
# ---------------------------------------------------------------------------

@dataclass
class TokenInfo:
    """
    Metadata for a registered Bearer token.

    The plaintext token is NEVER stored. Only the SHA-256 hash is kept as the
    dictionary key. This dataclass holds the associated metadata.

    Fields:
        user_id:    Identifier of the token owner.
        scopes:     List of granted OAuth3 scopes.
        expires_at: UTC datetime when the token expires.
        revoked:    True if the token has been explicitly revoked.
        created_at: UTC datetime when the token was registered.
    """
    user_id: str
    scopes: list[str] = field(default_factory=list)
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SessionTokenInfo:
    """
    Metadata for a session-scoped token issued during WebSocket upgrade.

    Fields:
        user_id:       Identifier of the session owner.
        scopes:        Inherited scopes from the Bearer token.
        expires_at:    UTC datetime when the session expires (5 min TTL).
        bearer_hash:   SHA-256 hash of the originating Bearer token.
        created_at:    UTC datetime when the session token was issued.
    """
    user_id: str
    scopes: list[str] = field(default_factory=list)
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bearer_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Token hashing (never store plaintext)
# ---------------------------------------------------------------------------

def hash_token(token: str) -> str:
    """
    Compute SHA-256 hash of a token string.

    Used as the dictionary key for token lookup. The plaintext token
    is never stored — only this hash is persisted in memory.

    Args:
        token: The raw Bearer token string.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Token format validation
# ---------------------------------------------------------------------------

def validate_token_format(token: str) -> bool:
    """
    Validate that a token string matches the sw_sk_ format.

    Format: sw_sk_ prefix followed by at least 8 alphanumeric/underscore/hyphen chars.

    Args:
        token: The raw token string to validate.

    Returns:
        True if format is valid.
    """
    return bool(_TOKEN_FORMAT_RE.match(token))


# ---------------------------------------------------------------------------
# AuthProxy — the 3-layer defense proxy
# ---------------------------------------------------------------------------

class AuthProxy:
    """
    3-layer defense proxy for Chromium CDP access.

    Layer 1: HTTP proxy on port 8888 that validates Bearer tokens.
    Layer 2: Forward authenticated requests to Chromium CDP on port 9225.
    Layer 3: Session token exchange for WebSocket connections.

    Usage:
        proxy = AuthProxy(proxy_port=8888, cdp_port=9225)
        proxy.register_token("sw_sk_abc123def456", TokenInfo(
            user_id="user@example.com",
            scopes=["browser.read.dom"],
            expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        ))
        proxy.start()
        # ... later ...
        proxy.stop()
    """

    def __init__(
        self,
        *,
        proxy_port: int = DEFAULT_PROXY_PORT,
        cdp_port: int = DEFAULT_CDP_PORT,
        bind_host: str = DEFAULT_BIND_HOST,
        now_fn: Any | None = None,
    ) -> None:
        """
        Initialize the auth proxy.

        Args:
            proxy_port: Port for the auth proxy to listen on (default 8888).
            cdp_port:   Port where Chromium CDP is listening (default 9225).
            bind_host:  Host to bind to (default 127.0.0.1 — localhost only).
            now_fn:     Optional callable returning current UTC datetime (for testing).

        Raises:
            ValueError: If proxy_port == cdp_port (would create a loop).
        """
        if proxy_port == cdp_port:
            raise ValueError(
                f"proxy_port ({proxy_port}) must differ from cdp_port ({cdp_port}). "
                "Identical ports would create a forwarding loop."
            )

        self._proxy_port = proxy_port
        self._cdp_port = cdp_port
        self._bind_host = bind_host
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

        # Token stores (in-memory only, keyed by SHA-256 hash)
        self._tokens: dict[str, TokenInfo] = {}
        self._session_tokens: dict[str, SessionTokenInfo] = {}

        # Lock for thread-safe token operations
        self._lock = threading.Lock()

        # Server instance (set on start)
        self._server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None

    # -----------------------------------------------------------------------
    # Token management
    # -----------------------------------------------------------------------

    def register_token(self, token: str, info: TokenInfo) -> str:
        """
        Register a Bearer token in the in-memory store.

        The plaintext token is hashed immediately. Only the hash is stored
        as the dictionary key. The plaintext is never persisted.

        Args:
            token: The raw Bearer token string (must match sw_sk_ format).
            info:  TokenInfo with user_id, scopes, expires_at.

        Returns:
            The SHA-256 hash of the token (for revocation reference).

        Raises:
            ValueError: If token format is invalid.
        """
        if not validate_token_format(token):
            raise ValueError(
                f"Token format invalid. Must match: {TOKEN_PREFIX}<8+ alphanumeric chars>. "
                f"Got: {token[:10]}..."
            )
        token_hash = hash_token(token)
        with self._lock:
            self._tokens[token_hash] = info
        return token_hash

    def validate_token(self, token: str) -> TokenInfo | None:
        """
        Validate a Bearer token and return its info if valid.

        Checks (in order, fail-closed):
        1. Format: must match sw_sk_ prefix + min length
        2. Registered: hash must exist in token store
        3. Not revoked: revoked flag must be False
        4. Not expired: expires_at must be in the future

        Args:
            token: The raw Bearer token string.

        Returns:
            TokenInfo if valid, None otherwise.
        """
        # Step 1: Format check
        if not validate_token_format(token):
            return None

        # Step 2: Lookup by hash (never compare plaintext)
        token_hash = hash_token(token)
        with self._lock:
            info = self._tokens.get(token_hash)
        if info is None:
            return None

        # Step 3: Revocation check
        if info.revoked:
            return None

        # Step 4: Expiry check (no extension, no renewal)
        now = self._now_fn()
        if now >= info.expires_at:
            return None

        return info

    def validate_token_detailed(self, token: str) -> tuple[TokenInfo | None, str]:
        """
        Validate a Bearer token and return detailed rejection reason.

        Returns:
            (TokenInfo | None, reason_string)
            reason is empty string on success, or one of:
            "invalid_format", "unknown_token", "token_revoked", "token_expired"
        """
        if not validate_token_format(token):
            return None, "invalid_format"

        token_hash = hash_token(token)
        with self._lock:
            info = self._tokens.get(token_hash)
        if info is None:
            return None, "unknown_token"

        if info.revoked:
            return None, "token_revoked"

        now = self._now_fn()
        if now >= info.expires_at:
            return None, "token_expired"

        return info, ""

    def revoke_token(self, token_hash: str) -> bool:
        """
        Revoke a token by its hash.

        Args:
            token_hash: SHA-256 hash of the token to revoke.

        Returns:
            True if the token was found and revoked, False if not found.
        """
        with self._lock:
            info = self._tokens.get(token_hash)
            if info is None:
                return False
            info.revoked = True
        return True

    def issue_session_token(self, bearer_token: str) -> dict[str, Any] | None:
        """
        Exchange a valid Bearer token for a short-lived session token (Layer 3).

        The session token is used for WebSocket connections. It inherits the
        scopes from the Bearer token and has a 5-minute TTL.

        Args:
            bearer_token: The raw Bearer token to exchange.

        Returns:
            Dict with session_token, ws_url, expires_in on success.
            None if the Bearer token is invalid.
        """
        info = self.validate_token(bearer_token)
        if info is None:
            return None

        now = self._now_fn()
        session_token = SESSION_TOKEN_PREFIX + secrets.token_urlsafe(32)
        session_hash = hash_token(session_token)
        session_info = SessionTokenInfo(
            user_id=info.user_id,
            scopes=list(info.scopes),
            expires_at=datetime.fromtimestamp(
                now.timestamp() + SESSION_TOKEN_TTL_SECONDS,
                tz=timezone.utc,
            ),
            bearer_hash=hash_token(bearer_token),
            created_at=now,
        )

        with self._lock:
            self._session_tokens[session_hash] = session_info

        return {
            "session_token": session_token,
            "ws_url": f"ws://{self._bind_host}:{self._proxy_port}",
            "expires_in": SESSION_TOKEN_TTL_SECONDS,
            "user_id": info.user_id,
            "scopes": list(info.scopes),
        }

    def validate_session_token(self, session_token: str) -> SessionTokenInfo | None:
        """
        Validate a session token.

        Args:
            session_token: The raw session token string.

        Returns:
            SessionTokenInfo if valid, None otherwise.
        """
        if not session_token.startswith(SESSION_TOKEN_PREFIX):
            return None

        session_hash = hash_token(session_token)
        with self._lock:
            info = self._session_tokens.get(session_hash)
        if info is None:
            return None

        now = self._now_fn()
        if now >= info.expires_at:
            return None

        return info

    @property
    def token_count(self) -> int:
        """Number of registered Bearer tokens."""
        with self._lock:
            return len(self._tokens)

    @property
    def session_token_count(self) -> int:
        """Number of active session tokens."""
        with self._lock:
            return len(self._session_tokens)

    # -----------------------------------------------------------------------
    # Proxy server lifecycle
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """
        Start the auth proxy server in a background thread.

        The server listens on bind_host:proxy_port and forwards authenticated
        requests to localhost:cdp_port.

        Raises:
            RuntimeError: If the server is already running.
            OSError: If the port is already in use.
        """
        if self._server is not None:
            raise RuntimeError("Auth proxy is already running.")

        handler_class = _build_handler_class(self)
        self._server = ThreadingHTTPServer(
            (self._bind_host, self._proxy_port),
            handler_class,
        )
        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="auth-proxy",
            daemon=True,
        )
        self._server_thread.start()
        logger.info(
            "Auth proxy started on %s:%d -> localhost:%d",
            self._bind_host, self._proxy_port, self._cdp_port,
        )

    def stop(self) -> None:
        """
        Stop the auth proxy server.

        Blocks until the server thread has finished. Cleans up the server
        socket. Does nothing if the server is not running.
        """
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._server_thread is not None:
            self._server_thread.join(timeout=5.0)
        self._server = None
        self._server_thread = None
        logger.info("Auth proxy stopped.")

    @property
    def is_running(self) -> bool:
        """True if the proxy server is currently running."""
        return self._server is not None

    @property
    def proxy_port(self) -> int:
        """The port the auth proxy listens on."""
        return self._proxy_port

    @property
    def cdp_port(self) -> int:
        """The port Chromium CDP is expected on."""
        return self._cdp_port

    # -----------------------------------------------------------------------
    # Internal: forward request to CDP
    # -----------------------------------------------------------------------

    def forward_to_cdp(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        """
        Forward an authenticated HTTP request to the CDP backend.

        Connects to localhost:cdp_port. Returns the CDP response.

        Args:
            method:  HTTP method (GET, POST, etc.).
            path:    Request path.
            headers: Request headers (Authorization stripped).
            body:    Request body (for POST/PUT).

        Returns:
            Tuple of (status_code, response_headers, response_body).

        Raises:
            ConnectionRefusedError: If CDP is not running on cdp_port.
            OSError: If connection to CDP fails.
        """
        conn = http.client.HTTPConnection(
            "127.0.0.1",
            self._cdp_port,
            timeout=10,
        )
        try:
            # Strip Authorization header before forwarding
            forward_headers = {
                k: v for k, v in headers.items()
                if k.lower() != "authorization"
            }
            conn.request(method, path, body=body, headers=forward_headers)
            response = conn.getresponse()
            response_body = response.read()
            response_headers = dict(response.getheaders())
            return response.status, response_headers, response_body
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------

def _extract_bearer_token(authorization: str | None) -> str | None:
    """
    Extract the Bearer token from an Authorization header value.

    Args:
        authorization: The Authorization header value (e.g., "Bearer sw_sk_abc123").

    Returns:
        The token string if present, None otherwise.
    """
    if authorization is None:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2:
        return None
    if parts[0].lower() != "bearer":
        return None
    return parts[1]


def _build_handler_class(proxy: AuthProxy) -> type[BaseHTTPRequestHandler]:
    """
    Build an HTTP request handler class bound to the given AuthProxy instance.

    Returns a handler class (not an instance) suitable for ThreadingHTTPServer.
    """

    class AuthProxyHandler(BaseHTTPRequestHandler):
        """HTTP handler that validates Bearer tokens before forwarding to CDP."""

        _proxy: AuthProxy = proxy

        def do_GET(self) -> None:  # noqa: N802
            self._handle_request("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle_request("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._handle_request("PUT")

        def do_DELETE(self) -> None:  # noqa: N802
            self._handle_request("DELETE")

        def do_HEAD(self) -> None:  # noqa: N802
            self._handle_request("HEAD")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._handle_request("OPTIONS")

        def _handle_request(self, method: str) -> None:
            """
            Central request handler. Validates auth, then forwards or rejects.

            Flow:
            1. Check for session start endpoint (Layer 3)
            2. Extract and validate Bearer token
            3. On success: forward to CDP backend
            4. On failure: return 401 with JSON error body
            """
            request_path = urlsplit(self.path).path

            # Layer 3: Session token exchange endpoint
            if request_path == "/api/session/start" and method == "POST":
                self._handle_session_start()
                return

            # Layer 3: WebSocket upgrade with session token (query param)
            query = parse_qs(urlsplit(self.path).query)
            ws_token = query.get("token", [None])[0]
            if ws_token is not None and ws_token.startswith(SESSION_TOKEN_PREFIX):
                session_info = self._proxy.validate_session_token(ws_token)
                if session_info is None:
                    self._send_json_error(HTTPStatus.UNAUTHORIZED, _UNAUTHORIZED_BODY)
                    return
                # Session token valid — forward to CDP
                self._forward_to_cdp(method)
                return

            # Layer 1: Extract Bearer token from Authorization header
            auth_header = self.headers.get("Authorization")
            token = _extract_bearer_token(auth_header)

            if token is None:
                self._send_json_error(HTTPStatus.UNAUTHORIZED, _UNAUTHORIZED_BODY)
                return

            # Validate token (fail-closed: format + registered + not revoked + not expired)
            info, reason = self._proxy.validate_token_detailed(token)
            if info is None:
                if reason == "token_expired":
                    self._send_json_error(HTTPStatus.UNAUTHORIZED, _EXPIRED_BODY)
                elif reason == "token_revoked":
                    self._send_json_error(HTTPStatus.UNAUTHORIZED, _REVOKED_BODY)
                else:
                    self._send_json_error(HTTPStatus.UNAUTHORIZED, _UNAUTHORIZED_BODY)
                return

            # Token valid — forward to CDP backend (Layer 2)
            self._forward_to_cdp(method)

        def _handle_session_start(self) -> None:
            """
            Handle POST /api/session/start — exchange Bearer for session token.

            Reads Bearer token from Authorization header, validates it, then
            issues a short-lived session token for WebSocket access.
            """
            auth_header = self.headers.get("Authorization")
            token = _extract_bearer_token(auth_header)

            if token is None:
                self._send_json_error(HTTPStatus.UNAUTHORIZED, _UNAUTHORIZED_BODY)
                return

            result = self._proxy.issue_session_token(token)
            if result is None:
                self._send_json_error(HTTPStatus.UNAUTHORIZED, _UNAUTHORIZED_BODY)
                return

            body = json.dumps(result).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _forward_to_cdp(self, method: str) -> None:
            """
            Forward the authenticated request to the Chromium CDP backend.

            Reads the request body (for POST/PUT), forwards to CDP, and
            relays the CDP response back to the client.
            """
            # Read request body if present
            content_length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # Collect headers for forwarding (strip Authorization)
            forward_headers: dict[str, str] = {}
            for key in self.headers:
                if key.lower() != "authorization":
                    forward_headers[key] = self.headers[key]

            try:
                status, resp_headers, resp_body = self._proxy.forward_to_cdp(
                    method, self.path, forward_headers, body,
                )
            except ConnectionRefusedError:
                error_body = json.dumps({
                    "error": "cdp_unavailable",
                    "message": "Chromium CDP is not running on the expected port.",
                }).encode("utf-8")
                self.send_response(HTTPStatus.BAD_GATEWAY)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(error_body)))
                self.end_headers()
                self.wfile.write(error_body)
                return
            except OSError as exc:
                error_body = json.dumps({
                    "error": "cdp_connection_failed",
                    "message": f"Failed to connect to CDP: {exc}",
                }).encode("utf-8")
                self.send_response(HTTPStatus.BAD_GATEWAY)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(error_body)))
                self.end_headers()
                self.wfile.write(error_body)
                return

            # Relay CDP response
            self.send_response(status)
            for key, value in resp_headers.items():
                if key.lower() not in ("transfer-encoding",):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(resp_body)

        def _send_json_error(self, status: HTTPStatus, body: bytes) -> None:
            """Send a JSON error response."""
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            """Route HTTP server logs through the auth_proxy logger."""
            logger.debug("[auth-proxy] %s", format % args)

    return AuthProxyHandler

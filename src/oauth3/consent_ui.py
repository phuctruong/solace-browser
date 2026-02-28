"""
OAuth3 Consent UI — SolaceBrowser Phase 1.5 BUILD 2

Routes (all served from the aiohttp server on port 9222):
  GET  /consent                 — Consent page (show scope list, grant/deny)
  POST /oauth3/consent          — Consent handler (issue token, set cookie, redirect)
  GET  /settings/tokens         — Token management page (list + revoke)
  DELETE /oauth3/token/{id}     — Revoke a token (via fetch() from token page)

Home page tiles with scope badge are injected via build_home_page_with_badges().

Design:
  - Vanilla HTML / CSS / JS — no build step, no frameworks
  - Dark theme matching existing SolaceBrowserServer._get_ui_html()
  - All HTML generation is pure string building (no template engine)
  - Fail-closed: unknown scopes → 400, open-redirect sanitised

Rung: 641
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Resolve src/ path so oauth3 imports work when this module is used standalone
# ---------------------------------------------------------------------------

_SRC_PATH = Path(__file__).parent.parent
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from oauth3.token import AgencyToken, DEFAULT_TOKEN_DIR
from oauth3.scopes import (
    SCOPES,
    STEP_UP_REQUIRED_SCOPES,
    validate_scopes,
    validate_scopes_lenient,
    get_scope_description,
    get_scope_risk_level,
)
from oauth3.revocation import revoke_token, list_all_tokens
from oauth3.step_up import create_step_up_nonce

# ---------------------------------------------------------------------------
# Platform → default scopes mapping (for home page tile badges)
# ---------------------------------------------------------------------------

PLATFORM_DEFAULT_SCOPES: dict = {
    "linkedin": [
        "linkedin.read_messages",
        "linkedin.create_post",
        "linkedin.edit_post",
        "linkedin.react",
        "linkedin.comment",
    ],
    "gmail": [
        "gmail.read_inbox",
        "gmail.send_email",
        "gmail.search",
        "gmail.label",
    ],
    "reddit": [
        "reddit.create_post",
        "reddit.comment",
        "reddit.upvote",
    ],
    "hackernews": [
        "hackernews.submit",
        "hackernews.comment",
    ],
    "github": [],
    "google": [],
}

# ---------------------------------------------------------------------------
# Open-redirect sanitiser
# ---------------------------------------------------------------------------

_SAFE_REDIRECT_PATTERN = re.compile(r"^/[^/\\].*$")


def sanitise_redirect(redirect: str, default: str = "/") -> str:
    """
    Allow only same-origin relative redirects.
    Blocks:
      - Absolute URLs (http://evil.com)
      - Protocol-relative URLs (//evil.com)
      - Any non-string or empty values

    Args:
        redirect: The redirect path from user input.
        default: Fallback path when redirect is unsafe.

    Returns:
        The sanitised redirect path.
    """
    if not isinstance(redirect, str):
        return default
    redirect = redirect.strip()
    if not redirect:
        return default
    # Must start with single '/' and not be '//' (protocol-relative)
    if _SAFE_REDIRECT_PATTERN.match(redirect):
        return redirect
    return default


# ---------------------------------------------------------------------------
# HTML helpers — dark theme matching existing UI
# ---------------------------------------------------------------------------

def _h(text: str) -> str:
    """HTML-escape a string."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _html_shell(title: str, body: str) -> str:
    """Wrap body in a full HTML document with dark theme."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_h(title)} - SolaceBrowser</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #030712;
      color: #f9fafb;
      min-height: 100vh;
    }}
    nav {{
      background: #111827;
      border-bottom: 1px solid #374151;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}
    nav .brand {{ font-size: 1.1rem; font-weight: 700; color: #60a5fa; }}
    nav .nav-links a {{
      color: #9ca3af;
      text-decoration: none;
      font-size: 0.875rem;
      margin-left: 16px;
    }}
    nav .nav-links a:hover {{ color: #f9fafb; }}
    .container {{
      max-width: 640px;
      margin: 48px auto;
      padding: 0 24px;
    }}
    .card {{
      background: #1f2937;
      border: 1px solid #374151;
      border-radius: 12px;
      padding: 32px;
    }}
    .card-header {{
      margin-bottom: 24px;
    }}
    .card-header h1 {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #f9fafb;
      margin-bottom: 8px;
    }}
    .card-header p {{
      color: #9ca3af;
      font-size: 0.875rem;
    }}
    .app-badge {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #374151;
      border: 1px solid #4b5563;
      border-radius: 8px;
      padding: 8px 14px;
      margin-bottom: 20px;
    }}
    .app-badge .icon {{
      width: 28px;
      height: 28px;
      background: #3b82f6;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      font-weight: 700;
      color: white;
    }}
    .app-badge .name {{
      font-weight: 600;
      font-size: 0.9rem;
    }}
    .scope-list {{
      list-style: none;
      margin-bottom: 20px;
    }}
    .scope-item {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 0;
      border-bottom: 1px solid #374151;
    }}
    .scope-item:last-child {{ border-bottom: none; }}
    .scope-icon {{
      font-size: 1.1rem;
      width: 28px;
      text-align: center;
      flex-shrink: 0;
      margin-top: 2px;
    }}
    .scope-info {{ flex: 1; }}
    .scope-name {{
      font-size: 0.8rem;
      font-family: 'Courier New', monospace;
      color: #93c5fd;
      margin-bottom: 2px;
    }}
    .scope-desc {{
      font-size: 0.875rem;
      color: #e5e7eb;
    }}
    .risk-badge {{
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 99px;
      flex-shrink: 0;
      margin-top: 3px;
    }}
    .risk-low {{ background: #14532d; color: #86efac; }}
    .risk-medium {{ background: #713f12; color: #fde68a; }}
    .risk-high {{ background: #7f1d1d; color: #fca5a5; }}
    .step-up-banner {{
      background: #422006;
      border: 1px solid #92400e;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 20px;
      font-size: 0.875rem;
      color: #fbbf24;
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .btn-row {{
      display: flex;
      gap: 12px;
      margin-top: 24px;
    }}
    .btn {{
      flex: 1;
      padding: 10px 20px;
      border-radius: 8px;
      border: none;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      text-decoration: none;
      display: block;
    }}
    .btn-allow {{
      background: #2563eb;
      color: white;
    }}
    .btn-allow:hover {{ background: #1d4ed8; }}
    .btn-deny {{
      background: #374151;
      color: #9ca3af;
    }}
    .btn-deny:hover {{ background: #4b5563; color: #f9fafb; }}
    /* Token management page */
    .page-title {{
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 24px;
    }}
    .token-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }}
    .token-table th {{
      text-align: left;
      padding: 10px 12px;
      background: #111827;
      border-bottom: 1px solid #374151;
      color: #9ca3af;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .token-table td {{
      padding: 12px;
      border-bottom: 1px solid #1f2937;
      vertical-align: top;
    }}
    .token-table tr:last-child td {{ border-bottom: none; }}
    .token-table tr.revoked td {{ opacity: 0.45; }}
    .token-id-cell {{ font-family: 'Courier New', monospace; color: #93c5fd; }}
    .status-active {{
      display: inline-block;
      width: 8px; height: 8px;
      background: #22c55e;
      border-radius: 50%;
      margin-right: 6px;
    }}
    .status-revoked {{
      display: inline-block;
      width: 8px; height: 8px;
      background: #6b7280;
      border-radius: 50%;
      margin-right: 6px;
    }}
    .revoke-btn {{
      background: #7f1d1d;
      color: #fca5a5;
      border: none;
      border-radius: 5px;
      padding: 4px 10px;
      font-size: 0.75rem;
      cursor: pointer;
      font-weight: 600;
    }}
    .revoke-btn:hover {{ background: #991b1b; }}
    .tag-chip {{
      display: inline-block;
      background: #1e3a5f;
      color: #93c5fd;
      border-radius: 4px;
      padding: 2px 7px;
      font-size: 0.7rem;
      margin: 1px;
      font-family: 'Courier New', monospace;
    }}
    .empty-state {{
      padding: 40px;
      text-align: center;
      color: #6b7280;
    }}
    /* Home page scope badge */
    .scope-badge-green {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #14532d;
      color: #86efac;
      border-radius: 9999px;
      padding: 2px 9px;
      font-size: 0.7rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .scope-badge-gray {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #374151;
      color: #9ca3af;
      border-radius: 9999px;
      padding: 2px 9px;
      font-size: 0.7rem;
      font-weight: 600;
      cursor: pointer;
    }}
    .scope-badge-gray:hover {{ background: #4b5563; }}
    .flash-error {{
      background: #7f1d1d;
      border: 1px solid #991b1b;
      color: #fca5a5;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 16px;
      font-size: 0.875rem;
    }}
  </style>
</head>
<body>
  <nav>
    <span class="brand">SolaceBrowser</span>
    <div class="nav-links">
      <a href="/">Home</a>
      <a href="/settings/tokens">Tokens</a>
    </div>
  </nav>
  {body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Icon helpers
# ---------------------------------------------------------------------------

def _scope_icon(scope: str, risk: str) -> str:
    """Return an emoji icon for the scope based on action class."""
    if risk == "high":
        return "&#x1F5D1;"   # trash
    action = scope.split(".")[-1] if "." in scope else scope
    read_actions = {"read_messages", "read_inbox", "search", "get_stats",
                    "read_timeline", "check_notifications", "read_page"}
    if action in read_actions:
        return "&#x1F441;"   # eye
    return "&#x270F;"         # pencil


# ---------------------------------------------------------------------------
# Page builder: GET /consent
# ---------------------------------------------------------------------------

def build_consent_page(
    scopes_param: str,
    redirect: str = "/",
    error: Optional[str] = None,
    token_dir: Optional[Path] = None,
) -> tuple[str, int]:
    """
    Build the consent page HTML.

    Args:
        scopes_param: Comma-separated scope string from query param.
        redirect: Where to redirect after granting.
        error: Optional error message to show (e.g. from a previous failed attempt).
        token_dir: Token directory (for testability; defaults to DEFAULT_TOKEN_DIR).

    Returns:
        (html_str, http_status_code)
        Returns 400 for unknown scopes, 200 otherwise.
    """
    safe_redirect = sanitise_redirect(redirect)

    # Parse and validate scopes
    requested_scopes = [s.strip() for s in scopes_param.split(",") if s.strip()]
    if not requested_scopes:
        return _html_shell(
            "Permission Request",
            '<div class="container"><div class="flash-error">No scopes requested.</div></div>',
        ), 400

    is_valid, unknown = validate_scopes_lenient(requested_scopes)
    if not is_valid:
        unknown_list = ", ".join(_h(u) for u in unknown)
        body = (
            '<div class="container">'
            f'<div class="flash-error">Unknown scope(s): {unknown_list}</div>'
            '</div>'
        )
        return _html_shell("Permission Request", body), 400

    # Check for step-up scopes in requested list
    has_step_up = any(s in STEP_UP_REQUIRED_SCOPES for s in requested_scopes)

    # Build scope list HTML
    scope_items = ""
    for scope in requested_scopes:
        desc = get_scope_description(scope) or scope
        risk = get_scope_risk_level(scope)
        icon = _scope_icon(scope, risk)
        risk_label = {"high": "HIGH RISK", "medium": "Medium", "low": "Low"}.get(risk, risk)
        risk_class = f"risk-{risk}"
        scope_items += f"""
    <li class="scope-item">
      <span class="scope-icon">{icon}</span>
      <div class="scope-info">
        <div class="scope-name">{_h(scope)}</div>
        <div class="scope-desc">{_h(desc)}</div>
      </div>
      <span class="risk-badge {risk_class}">{risk_label}</span>
    </li>"""

    # Step-up warning banner
    step_up_banner = ""
    if has_step_up:
        step_up_scopes = [s for s in requested_scopes if s in STEP_UP_REQUIRED_SCOPES]
        step_up_names = ", ".join(_h(s) for s in step_up_scopes)
        step_up_banner = f"""
  <div class="step-up-banner">
    <span>&#x26A0;</span>
    <span>Some requested scopes are <strong>destructive</strong> ({step_up_names}) and will require
    step-up confirmation before each use.</span>
  </div>"""

    # Error flash
    error_html = ""
    if error:
        error_html = f'<div class="flash-error">{_h(error)}</div>'

    scopes_json = json.dumps(requested_scopes)
    safe_redirect_escaped = _h(safe_redirect)

    body = f"""
  <div class="container">
    {error_html}
    <div class="card">
      <div class="card-header">
        <h1>SolaceBrowser is requesting permission</h1>
        <p>Review the permissions below before granting access.</p>
      </div>

      <div class="app-badge">
        <div class="icon">S</div>
        <div class="name">SolaceBrowser (local)</div>
      </div>

      {step_up_banner}

      <p style="font-size:0.8rem;color:#6b7280;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.05em;">
        Requested Permissions
      </p>
      <ul class="scope-list" id="scope-list">
        {scope_items}
      </ul>

      <div class="btn-row">
        <button class="btn btn-allow" onclick="grantConsent()">
          Allow &mdash; Grant Permission
        </button>
        <a class="btn btn-deny" href="/?error=access_denied">
          Deny &mdash; Cancel
        </a>
      </div>
    </div>
  </div>

  <script>
    const SCOPES = {scopes_json};
    const REDIRECT = {json.dumps(safe_redirect)};

    async function grantConsent() {{
      const btn = document.querySelector('.btn-allow');
      btn.disabled = true;
      btn.textContent = 'Granting...';
      try {{
        const resp = await fetch('/oauth3/consent', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify({{scopes: SCOPES, redirect: REDIRECT}})
        }});
        if (resp.redirected) {{
          window.location.href = resp.url;
          return;
        }}
        const data = await resp.json();
        if (data.redirect) {{
          window.location.href = data.redirect;
        }} else if (data.error) {{
          alert('Error: ' + data.error);
          btn.disabled = false;
          btn.textContent = 'Allow \u2014 Grant Permission';
        }} else {{
          window.location.href = REDIRECT;
        }}
      }} catch (e) {{
        alert('Network error: ' + e.message);
        btn.disabled = false;
        btn.textContent = 'Allow \u2014 Grant Permission';
      }}
    }}
  </script>"""

    return _html_shell("Permission Request", body), 200


# ---------------------------------------------------------------------------
# Page builder: GET /settings/tokens
# ---------------------------------------------------------------------------

def build_tokens_page(token_dir: Optional[Path] = None) -> str:
    """
    Build the token management page HTML.

    Args:
        token_dir: Token directory (for testability).

    Returns:
        HTML string for the /settings/tokens page.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR
    tokens = list_all_tokens(token_dir=token_dir)

    if not tokens:
        rows_html = (
            '<tr><td colspan="6" class="empty-state">'
            'No tokens issued yet. '
            '<a href="/consent?scopes=linkedin.create_post&redirect=/" '
            'style="color:#60a5fa">Grant your first permission</a>.'
            '</td></tr>'
        )
    else:
        rows_html = ""
        for token in tokens:
            revoked = token.revoked
            row_class = "revoked" if revoked else ""
            status_dot = "status-revoked" if revoked else "status-active"
            status_text = "Revoked" if revoked else "Active"
            status_color = "#6b7280" if revoked else "#22c55e"

            tid_short = token.token_id[:8]
            issued = token.issued_at[:19].replace("T", " ") if token.issued_at else ""
            expires = token.expires_at[:19].replace("T", " ") if token.expires_at else ""

            scope_chips = "".join(
                f'<span class="tag-chip">{_h(s)}</span>' for s in token.scopes
            )

            revoke_btn = ""
            if not revoked:
                revoke_btn = (
                    f'<button class="revoke-btn" '
                    f'onclick="revokeToken(\'{_h(token.token_id)}\')">'
                    f'Revoke</button>'
                )

            rows_html += f"""
      <tr class="{row_class}" id="row-{_h(token.token_id)}">
        <td class="token-id-cell" title="{_h(token.token_id)}">{_h(tid_short)}&hellip;</td>
        <td>{scope_chips}</td>
        <td style="color:#9ca3af;font-size:0.75rem">{_h(issued)}</td>
        <td style="color:#9ca3af;font-size:0.75rem">{_h(expires)}</td>
        <td>
          <span class="{status_dot}"></span>
          <span style="color:{status_color};font-size:0.8rem">{status_text}</span>
        </td>
        <td>{revoke_btn}</td>
      </tr>"""

    body = f"""
  <div class="container" style="max-width:900px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px;">
      <h1 class="page-title" style="margin-bottom:0">OAuth3 Token Management</h1>
      <a href="/consent?scopes=linkedin.create_post&redirect=/settings/tokens"
         style="background:#2563eb;color:white;padding:8px 16px;border-radius:8px;
                text-decoration:none;font-size:0.875rem;font-weight:600;">
        + Grant New Permission
      </a>
    </div>

    <div class="card" style="padding:0;overflow:hidden">
      <table class="token-table">
        <thead>
          <tr>
            <th>Token ID</th>
            <th>Scopes</th>
            <th>Issued</th>
            <th>Expires</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="token-tbody">
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    async function revokeToken(tokenId) {{
      if (!confirm('Revoke this token? This cannot be undone.')) return;
      const resp = await fetch('/oauth3/token/' + tokenId, {{method: 'DELETE'}});
      if (resp.ok) {{
        const row = document.getElementById('row-' + tokenId);
        if (row) {{
          row.classList.add('revoked');
          const btn = row.querySelector('.revoke-btn');
          if (btn) btn.remove();
          const dots = row.querySelectorAll('[class*="status-"]');
          dots.forEach(d => {{
            d.className = 'status-revoked';
            d.nextSibling.textContent = 'Revoked';
            d.nextSibling.style.color = '#6b7280';
          }});
        }}
      }} else {{
        alert('Failed to revoke token. It may already be revoked or not found.');
      }}
    }}
  </script>"""

    return _html_shell("Token Management", body)


# ---------------------------------------------------------------------------
# Scope badge helpers for home page injection
# ---------------------------------------------------------------------------

def get_platform_token_count(platform: str, token_dir: Optional[Path] = None) -> int:
    """
    Count active (non-revoked, non-expired) tokens that have at least one
    scope for the given platform.

    Args:
        platform: Platform name (e.g. "linkedin").
        token_dir: Token directory.

    Returns:
        Count of active tokens covering the platform.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR
    tokens = list_all_tokens(token_dir=token_dir)
    now = datetime.now(timezone.utc)
    prefix = f"{platform}."
    count = 0
    for token in tokens:
        if token.revoked:
            continue
        try:
            from oauth3.token import _parse_iso8601
            expires = _parse_iso8601(token.expires_at)
            if now > expires:
                continue
        except (TypeError, ValueError):
            continue
        if any(s.startswith(prefix) for s in token.scopes):
            count += 1
    return count


def build_scope_badge_html(platform: str, token_dir: Optional[Path] = None) -> str:
    """
    Build the HTML badge snippet for a platform tile on the home page.

    Returns either:
      - Green badge: "N scopes granted"
      - Gray badge: "No permissions — click to grant"

    Args:
        platform: Platform name.
        token_dir: Token directory (for testability).

    Returns:
        HTML snippet string.
    """
    token_dir = token_dir or DEFAULT_TOKEN_DIR
    tokens = list_all_tokens(token_dir=token_dir)
    now = datetime.now(timezone.utc)
    prefix = f"{platform}."
    total_scopes = 0
    for token in tokens:
        if token.revoked:
            continue
        try:
            from oauth3.token import _parse_iso8601
            expires = _parse_iso8601(token.expires_at)
            if now > expires:
                continue
        except (TypeError, ValueError):
            continue
        total_scopes += sum(1 for s in token.scopes if s.startswith(prefix))

    default_scopes = ",".join(PLATFORM_DEFAULT_SCOPES.get(platform, []))
    consent_url = f"/consent?scopes={default_scopes}&redirect=/"

    if total_scopes > 0:
        return (
            f'<a href="/settings/tokens" class="scope-badge-green">'
            f'&#x2714; {total_scopes} scope{"s" if total_scopes != 1 else ""} granted'
            f'</a>'
        )
    else:
        return (
            f'<a href="{_h(consent_url)}" class="scope-badge-gray">'
            f'No permissions &mdash; click to grant'
            f'</a>'
        )


# ---------------------------------------------------------------------------
# Route handlers (aiohttp-compatible coroutines)
# ---------------------------------------------------------------------------

async def handle_consent_get(request) -> object:
    """
    GET /consent?scopes=linkedin.create_post,linkedin.comment&redirect=/kanban

    Query params:
      scopes   — comma-separated scope list (required)
      redirect — where to go after granting (optional, default "/")
      error    — error message to flash (optional)
    """
    from aiohttp import web

    scopes_param = request.rel_url.query.get("scopes", "")
    redirect = request.rel_url.query.get("redirect", "/")
    error = request.rel_url.query.get("error")

    if not scopes_param:
        html, status = build_consent_page("", redirect=redirect, error=error)
    else:
        html, status = build_consent_page(scopes_param, redirect=redirect, error=error)

    return web.Response(text=html, content_type="text/html", status=status)


async def handle_consent_post(request) -> object:
    """
    POST /oauth3/consent
    Body: {"scopes": [...], "redirect": "/kanban"}

    Issues a token, sets HttpOnly SameSite=Strict cookie, returns JSON with redirect.
    The browser JS uses the JSON response to navigate; if the client follows redirects
    automatically (e.g. aiohttp follow_redirects=True), it will land on the target page.
    """
    from aiohttp import web

    try:
        data = await request.json()
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
        return web.json_response({"error": "invalid_json"}, status=400)

    requested_scopes = data.get("scopes", [])
    redirect = sanitise_redirect(data.get("redirect", "/"))

    if not requested_scopes:
        return web.json_response({"error": "missing_scopes"}, status=400)

    if not isinstance(requested_scopes, list):
        return web.json_response({"error": "scopes_must_be_list"}, status=400)

    is_valid, unknown = validate_scopes_lenient(requested_scopes)
    if not is_valid:
        return web.json_response(
            {"error": "unknown_scopes", "unknown": unknown},
            status=400,
        )

    # Issue token
    token = AgencyToken.create(
        user_id="local",
        scopes=requested_scopes,
    )
    token.save_to_file(DEFAULT_TOKEN_DIR)

    response = web.json_response(
        {
            "token_id": token.token_id,
            "scopes": token.scopes,
            "redirect": redirect,
        },
        status=200,
    )

    # Set HttpOnly, SameSite=Strict cookie
    response.set_cookie(
        "solace_agency_token",
        token.token_id,
        httponly=True,
        samesite="Strict",
        secure=True,
        max_age=token.expires_at and 60 * 60 * 24 * 30,  # 30 days
    )

    return response


async def handle_tokens_page(request) -> object:
    """GET /settings/tokens — Token management page."""
    from aiohttp import web

    html = build_tokens_page()
    return web.Response(text=html, content_type="text/html", status=200)


# ---------------------------------------------------------------------------
# Page builder: GET /step-up
# ---------------------------------------------------------------------------


def build_step_up_page(
    token_id: str,
    action: str,
    recipe_id: str = "",
    error: Optional[str] = None,
) -> tuple:
    """
    Build the step-up confirmation page HTML.

    Shown when a recipe requires a destructive scope (STEP_UP_REQUIRED_SCOPES).
    Forces the user to explicitly confirm the permanent, irreversible action.

    Args:
        token_id:  The agency token_id requesting the action.
        action:    The high-risk scope (e.g. "linkedin.delete_post").
        recipe_id: The recipe that triggered step-up (optional, for display).
        error:     Flash error message (e.g. "nonce expired").

    Returns:
        (html_str, http_status_code)
        Returns 400 if action is not a recognised step-up scope.
    """
    from oauth3.scopes import STEP_UP_REQUIRED_SCOPES, get_scope_description

    # Validate action is a real step-up scope
    if action not in STEP_UP_REQUIRED_SCOPES:
        body = (
            '<div class="container">'
            f'<div class="flash-error">Unknown or non-destructive action: {_h(action)}</div>'
            '</div>'
        )
        return _html_shell("Step-Up Confirmation", body), 400

    scope_desc = get_scope_description(action) or action

    error_html = ""
    if error:
        error_html = f'<div class="flash-error">{_h(error)}</div>'

    recipe_html = ""
    if recipe_id:
        recipe_html = f"""
      <div style="background:#111827;border:1px solid #374151;border-radius:8px;
                  padding:12px 16px;margin-bottom:20px;font-size:0.8rem;color:#9ca3af;">
        <strong style="color:#d1d5db;">Recipe:</strong>
        <code style="color:#93c5fd;margin-left:6px;">{_h(recipe_id)}</code>
      </div>"""

    # JSON payload for the POST request
    post_payload = json.dumps({"token_id": token_id, "action": action})

    body = f"""
  <div class="container">
    {error_html}
    <div class="card">
      <div class="card-header">
        <h1 style="color:#ef4444;">Permanent Action Confirmation</h1>
        <p style="color:#9ca3af;">Review carefully — this action cannot be undone.</p>
      </div>

      <!-- Red warning banner -->
      <div style="background:#450a0a;border:2px solid #dc2626;border-radius:10px;
                  padding:16px 20px;margin-bottom:24px;display:flex;
                  align-items:flex-start;gap:14px;">
        <span style="font-size:1.5rem;line-height:1;">&#9888;</span>
        <div>
          <div style="font-weight:700;color:#f87171;font-size:1rem;margin-bottom:4px;">
            Permanent Action &mdash; This cannot be undone
          </div>
          <div style="color:#fca5a5;font-size:0.875rem;">
            You are about to perform a destructive, irreversible action.
            Once confirmed, there is no undo.
          </div>
        </div>
      </div>

      <!-- Action details -->
      <div style="margin-bottom:20px;">
        <p style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;
                  letter-spacing:0.05em;margin-bottom:10px;">Action Being Authorised</p>
        <div style="display:flex;align-items:flex-start;gap:12px;padding:14px;
                    background:#1a1a2e;border:1px solid #4b5563;border-radius:8px;">
          <span style="font-size:1.2rem;">&#x1F5D1;</span>
          <div>
            <div style="font-family:'Courier New',monospace;color:#fca5a5;
                        font-size:0.85rem;margin-bottom:4px;">{_h(action)}</div>
            <div style="color:#e5e7eb;font-size:0.875rem;">{_h(scope_desc)}</div>
          </div>
          <span class="risk-badge risk-high" style="margin-left:auto;margin-top:2px;">
            HIGH RISK
          </span>
        </div>
      </div>

      {recipe_html}

      <!-- Confirm / Cancel -->
      <div class="btn-row">
        <button class="btn" id="confirm-btn"
                style="background:#dc2626;color:white;font-weight:700;"
                onclick="confirmStepUp()">
          &#x26A0; Confirm Delete
        </button>
        <a class="btn btn-deny" href="/">
          Cancel &mdash; Go Back
        </a>
      </div>

      <p style="margin-top:16px;font-size:0.75rem;color:#6b7280;text-align:center;">
        This confirmation expires in 5 minutes.
      </p>
    </div>
  </div>

  <script>
    const _PAYLOAD = {post_payload};

    async function confirmStepUp() {{
      const btn = document.getElementById('confirm-btn');
      btn.disabled = true;
      btn.textContent = 'Confirming...';
      try {{
        const resp = await fetch('/oauth3/step-up', {{
          method: 'POST',
          headers: {{'Content-Type': 'application/json'}},
          body: JSON.stringify(_PAYLOAD)
        }});
        const data = await resp.json();
        if (data.nonce) {{
          // Store nonce in sessionStorage and signal the originating tab / caller
          sessionStorage.setItem('solace_step_up_nonce', data.nonce);
          sessionStorage.setItem('solace_step_up_action', _PAYLOAD.action);
          // Redirect to a success notice page (caller should poll or use postMessage)
          window.location.href = '/?step_up=confirmed&action=' + encodeURIComponent(_PAYLOAD.action);
        }} else {{
          alert('Step-up failed: ' + (data.error || 'unknown error'));
          btn.disabled = false;
          btn.textContent = '\\u26A0 Confirm Delete';
        }}
      }} catch (e) {{
        alert('Network error: ' + e.message);
        btn.disabled = false;
        btn.textContent = '\\u26A0 Confirm Delete';
      }}
    }}
  </script>"""

    return _html_shell("Step-Up Confirmation", body), 200


# ---------------------------------------------------------------------------
# Route handlers: GET /step-up, POST /oauth3/step-up
# ---------------------------------------------------------------------------


async def handle_step_up_get(request) -> object:
    """
    GET /step-up?token_id=...&action=linkedin.delete_post&recipe_id=...

    Query params:
      token_id  — agency token that holds the destructive scope (required)
      action    — the step-up scope being confirmed (required)
      recipe_id — the recipe that triggered step-up (optional, display only)
      error     — error flash message (optional)
    """
    from aiohttp import web

    token_id = request.rel_url.query.get("token_id", "")
    action = request.rel_url.query.get("action", "")
    recipe_id = request.rel_url.query.get("recipe_id", "")
    error = request.rel_url.query.get("error")

    if not token_id or not action:
        html, status = _html_shell(
            "Step-Up Confirmation",
            '<div class="container"><div class="flash-error">'
            'Missing token_id or action parameter.</div></div>',
        ), 400
        return web.Response(text=html, content_type="text/html", status=status)

    html, status = build_step_up_page(
        token_id=token_id,
        action=action,
        recipe_id=recipe_id,
        error=error,
    )
    return web.Response(text=html, content_type="text/html", status=status)


async def handle_step_up_post(request) -> object:
    """
    POST /oauth3/step-up
    Body: {"token_id": "...", "action": "linkedin.delete_post"}

    Validates the token is active and has the destructive scope,
    then issues a one-time nonce (TTL 300s).

    Response 200: {"nonce": "uuid4", "expires_in": 300, "action": "..."}
    Response 400: invalid JSON or missing fields
    Response 401: token invalid / expired / revoked
    Response 403: token does not have the requested scope
    Response 422: action is not a step-up required scope
    """
    from aiohttp import web
    from oauth3.token import AgencyToken, DEFAULT_TOKEN_DIR
    from oauth3.scopes import STEP_UP_REQUIRED_SCOPES

    try:
        data = await request.json()
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError, ValueError):
        return web.json_response({"error": "invalid_json"}, status=400)

    token_id = data.get("token_id", "")
    action = data.get("action", "")

    if not token_id or not action:
        return web.json_response(
            {"error": "missing_fields", "detail": "token_id and action are required"},
            status=400,
        )

    # Validate action is actually a step-up scope
    if action not in STEP_UP_REQUIRED_SCOPES:
        return web.json_response(
            {
                "error": "not_step_up_scope",
                "detail": f"'{action}' is not a step-up required scope",
                "step_up_scopes": STEP_UP_REQUIRED_SCOPES,
            },
            status=422,
        )

    # Load and validate token
    try:
        token = AgencyToken.load_from_file(token_id)
    except FileNotFoundError:
        return web.json_response(
            {"error": "token_not_found", "token_id": token_id},
            status=401,
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        return web.json_response({"error": "token_load_error", "detail": str(e)}, status=401)

    is_valid, validity_error = token.validate()
    if not is_valid:
        error_code = "token_revoked" if token.revoked else "token_expired"
        return web.json_response(
            {"error": error_code, "detail": validity_error, "token_id": token_id},
            status=401,
        )

    # Token must have the requested scope
    if not token.has_scope(action):
        return web.json_response(
            {
                "error": "insufficient_scope",
                "detail": f"Token does not have scope '{action}'",
                "token_scopes": token.scopes,
            },
            status=403,
        )

    # All checks passed — issue nonce
    nonce = create_step_up_nonce(token_id=token_id, action=action)

    return web.json_response(
        {
            "nonce": nonce,
            "expires_in": 300,
            "action": action,
            "token_id": token_id,
        },
        status=200,
    )


# ---------------------------------------------------------------------------
# Route registration helper
# ---------------------------------------------------------------------------

def register_consent_routes(app) -> None:
    """
    Register all consent UI routes onto an aiohttp Application.

    Call this from SolaceBrowserServer._setup_routes().

    Args:
        app: aiohttp.web.Application instance.
    """
    app.router.add_get("/consent", handle_consent_get)
    app.router.add_post("/oauth3/consent", handle_consent_post)
    app.router.add_get("/settings/tokens", handle_tokens_page)
    app.router.add_get("/step-up", handle_step_up_get)
    app.router.add_post("/oauth3/step-up", handle_step_up_post)

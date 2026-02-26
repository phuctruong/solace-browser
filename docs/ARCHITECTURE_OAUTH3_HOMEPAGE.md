# Solace Browser: OAuth3 Multi-Site Homepage + Webservice Architecture
**Version:** 1.0.0
**Rung Target:** 641 (deterministic, testable, well-scoped design)
**Authority:** 65537
**Date:** 2026-02-23

---

## EXECUTIVE SUMMARY

This document specifies the architecture for a **multi-OAuth3 browser homepage + webservice enhancements** that enables unified session management across 6 authentication providers (Gmail, LinkedIn, GitHub, Twitter/X, Slack, Discord).

**Key design principles:**
- **Session-centric**: All OAuth3 tokens stored locally with symmetric encryption (AES-256-GCM)
- **Persistent context**: Browser maintains login state across restarts via artifacts/solace_session.json
- **Recipe-ready**: Homepage feeds per-provider session data into recipe execution engine
- **Evidence-bundled**: Every OAuth action logged to artifacts/oauth3/oauth3_audit.jsonl
- **Step-up ready**: Sensitive actions trigger additional consent challenge

---

## PART 1: HOMEPAGE HTML WIREFRAME & SPECIFICATIONS

### 1.1 Visual Layout (ASCII)

```
┌──────────────────────────────────────────────────────────────────────┐
│  🌊 SOLACE BROWSER — OAuth3 Portal                                  │
│  Universal AI agent browser. Local session manager + cloud exec.     │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ SESSION STATUS                                              │   │
│  │ 🟢 Uptime: 4h 23m  │  API Calls: 347  │  Storage: 2.3 MB   │   │
│  │ 🔐 Encrypted: Yes  │  Last action: 2026-02-23 14:52:30     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────┬──────────────┬─────────────┐                      │
│  │  📧 GMAIL   │  🔵 LINKEDIN │  🐙 GITHUB  │                      │
│  ├─────────────┼──────────────┼─────────────┤                      │
│  │ ✅ Authed   │ ❌ Not login │ ⚠️  Expired │                      │
│  │ Last: 2h    │              │ Last: 12d   │                      │
│  │             │              │             │                      │
│  │ [Check Mail]│ [Login]      │ [Refresh]   │                      │
│  │ [Compose]   │ [Settings]   │ [Settings]  │                      │
│  │ [Settings]  │              │             │                      │
│  └─────────────┴──────────────┴─────────────┘                      │
│                                                                      │
│  ┌─────────────┬──────────────┬─────────────┐                      │
│  │  🐦 TWITTER │  💬 SLACK    │  👾 DISCORD │                      │
│  ├─────────────┼──────────────┼─────────────┤                      │
│  │ ⚠️  Expired │ ✅ Authed    │ ✅ Authed   │                      │
│  │ Last: 12d   │ Last: 30m    │ Last: 1h    │                      │
│  │             │              │             │                      │
│  │ [Refresh]   │ [Check DMs]  │ [View]      │                      │
│  │ [Settings]  │ [Channels]   │ [Settings]  │                      │
│  │             │ [Settings]   │             │                      │
│  └─────────────┴──────────────┴─────────────┘                      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ GLOBAL ACTIONS                                               │  │
│  │ [Logout All]  [Export Session]  [Check for Expirations]     │  │
│  │ [Settings]    [Evidence Log]    [Diagnostics]               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Provider Card Specifications

**Each provider card displays:**

| Field | Example | Data Source | Refresh |
|-------|---------|-------------|---------|
| Icon | 📧, 🔵, 🐙 | config.json | Static |
| Name | "Gmail", "LinkedIn" | config.json | Static |
| Status | ✅, ❌, ⚠️ | OAuth3 token check | Real-time |
| Last Action | "Check Messages", "Post" | artifacts/oauth3_tokens.json | On load |
| Last Action Time | "2h ago", "12d ago" | artifacts/oauth3_tokens.json | On load |
| Token TTL | "Expires in 2h", "Expired" | artifacts/oauth3_tokens.json | Real-time |
| Quick Action Buttons | Provider-specific | data/default/recipes/ | Dynamic |

**Status determination logic:**

```python
def determine_provider_status(provider_id: str) -> dict:
    """
    Returns: {
        "status": "authenticated" | "not_logged_in" | "expired" | "needs_refresh",
        "icon": "✅" | "❌" | "⚠️" | "🔄",
        "last_action": str,
        "last_action_time": ISO8601,
        "token_ttl_seconds": int,
        "scopes_granted": [str],
    }
    """
    token = load_provider_token(provider_id)  # from artifacts/oauth3_tokens.json

    if token is None:
        return {"status": "not_logged_in", "icon": "❌"}

    if is_revoked(token.token_id):
        return {"status": "revoked", "icon": "❌"}

    now = datetime.now(timezone.utc)
    expires_at = parse_iso8601(token.expiry)
    ttl_seconds = (expires_at - now).total_seconds()

    if ttl_seconds < 0:
        return {"status": "expired", "icon": "⚠️", "token_ttl_seconds": 0}

    if ttl_seconds < 300:  # < 5 minutes
        return {"status": "needs_refresh", "icon": "🔄", "token_ttl_seconds": ttl_seconds}

    return {
        "status": "authenticated",
        "icon": "✅",
        "token_ttl_seconds": int(ttl_seconds),
        "scopes_granted": token.scopes,
        "last_action": token.last_action or "N/A",
        "last_action_time": token.last_action_time or token.issued_at,
    }
```

### 1.3 Quick Action Buttons

**Button mapping (provider-specific):**

```json
{
  "gmail": [
    {"label": "Check Mail", "action": "check_unread", "recipe_id": "gmail_check_unread_v1"},
    {"label": "Compose", "action": "compose_draft", "recipe_id": "gmail_compose_draft_v1"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://mail.google.com/mail/u/0/#settings"}
  ],
  "linkedin": [
    {"label": "Check DMs", "action": "view_messages", "recipe_id": "linkedin_check_dms_v1"},
    {"label": "View Feed", "action": "view_feed", "route": "/api/navigate?url=https://www.linkedin.com/feed/"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://www.linkedin.com/settings/"}
  ],
  "github": [
    {"label": "View Issues", "action": "list_issues", "recipe_id": "github_list_issues_v1"},
    {"label": "View PRs", "action": "list_prs", "recipe_id": "github_list_prs_v1"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://github.com/settings/"}
  ],
  "twitter": [
    {"label": "Check Feed", "action": "view_feed", "route": "/api/navigate?url=https://x.com/home"},
    {"label": "Compose", "action": "compose_tweet", "recipe_id": "twitter_compose_v1"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://x.com/settings/"}
  ],
  "slack": [
    {"label": "Check DMs", "action": "view_dms", "recipe_id": "slack_check_dms_v1"},
    {"label": "View Channels", "action": "list_channels", "recipe_id": "slack_list_channels_v1"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://app.slack.com/client/WORKSPACE_ID/preferences"}
  ],
  "discord": [
    {"label": "Check DMs", "action": "view_dms", "recipe_id": "discord_check_dms_v1"},
    {"label": "View Servers", "action": "list_servers", "recipe_id": "discord_list_servers_v1"},
    {"label": "Settings", "action": "open_settings", "route": "/api/navigate?url=https://discord.com/app"}
  ]
}
```

### 1.4 Session Info Panel

**Displays at bottom of homepage:**

```json
{
  "browser_uptime_seconds": 15780,
  "total_api_calls": 347,
  "last_action": "GET /api/oauth3/providers",
  "last_action_timestamp": "2026-02-23T14:52:30Z",
  "session_file_path": "artifacts/solace_session.json",
  "session_file_size_bytes": 2457600,
  "tokens_file_path": "artifacts/oauth3_tokens.json",
  "tokens_file_size_bytes": 15680,
  "cookies_count": 47,
  "local_storage_keys_count": 23,
  "storage_total_mb": 2.3,
  "persistent_context_enabled": true,
  "autosave_enabled": true,
  "autosave_seconds": 30,
  "encryption_status": "AES-256-GCM enabled",
  "evidence_audit_path": "artifacts/oauth3/oauth3_audit.jsonl",
  "audit_entries_count": 247
}
```

---

## PART 2: OAUTH3 WEBSERVICE API ENDPOINTS

All endpoints follow REST conventions. Base URL: `http://localhost:9223/api/oauth3`

### 2.1 GET /api/oauth3/providers

**Purpose:** Fetch all OAuth3 providers and their current session status.

**Request:**
```bash
curl http://localhost:9223/api/oauth3/providers
```

**Response (200 OK):**
```json
{
  "success": true,
  "providers": [
    {
      "id": "gmail",
      "name": "Gmail",
      "icon": "📧",
      "logo_url": "https://www.google.com/favicon.ico",
      "login_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
      "scopes": [
        {
          "name": "email",
          "description": "View your email address",
          "granted": true
        },
        {
          "name": "https://www.googleapis.com/auth/gmail.readonly",
          "description": "View your Gmail messages",
          "granted": true
        },
        {
          "name": "https://www.googleapis.com/auth/gmail.modify",
          "description": "Compose and send Gmail messages",
          "granted": false
        }
      ],
      "session_status": "authenticated",
      "session_status_icon": "✅",
      "session_expiry": "2026-02-25T10:30:00Z",
      "session_expiry_human": "in 1 day",
      "last_action": "read_message",
      "last_action_time": "2026-02-23T14:52:30Z",
      "last_action_time_human": "2 minutes ago",
      "token_ttl_seconds": 151200,
      "token_id": "token_gmail_20260223_abc123",
      "issued_at": "2026-02-23T10:30:00Z",
      "is_revoked": false,
      "can_refresh": true,
      "refresh_token_present": true
    },
    {
      "id": "linkedin",
      "name": "LinkedIn",
      "icon": "🔵",
      "logo_url": "https://www.linkedin.com/favicon.ico",
      "login_url": "https://www.linkedin.com/oauth/v2/authorization?client_id=...",
      "scopes": [],
      "session_status": "not_logged_in",
      "session_status_icon": "❌",
      "session_expiry": null,
      "last_action": null,
      "last_action_time": null,
      "token_ttl_seconds": 0,
      "token_id": null,
      "is_revoked": false
    },
    {
      "id": "github",
      "name": "GitHub",
      "icon": "🐙",
      "logo_url": "https://github.com/favicon.ico",
      "login_url": "https://github.com/login/oauth/authorize?client_id=...",
      "scopes": [
        {
          "name": "repo",
          "description": "Full access to private and public repositories",
          "granted": true
        },
        {
          "name": "user:email",
          "description": "Access to user email addresses",
          "granted": true
        }
      ],
      "session_status": "expired",
      "session_status_icon": "⚠️",
      "session_expiry": "2026-02-11T14:30:00Z",
      "session_expiry_human": "expired 12 days ago",
      "last_action": "view_issues",
      "last_action_time": "2026-02-11T14:35:00Z",
      "last_action_time_human": "12 days ago",
      "token_ttl_seconds": -1036800,
      "token_id": "token_github_20260211_xyz789",
      "issued_at": "2026-02-10T14:30:00Z",
      "is_revoked": false,
      "can_refresh": false,
      "refresh_token_present": false
    }
  ],
  "summary": {
    "total_providers": 6,
    "authenticated": 2,
    "not_logged_in": 2,
    "expired": 2,
    "needs_refresh": 0,
    "all_valid": false,
    "timestamp": "2026-02-23T14:52:30Z"
  }
}
```

**Error (400 Bad Request):**
```json
{
  "success": false,
  "error": "Token file not found or corrupted",
  "error_code": "TOKEN_LOAD_FAILED",
  "hint": "Run /api/oauth3/login to initialize a provider"
}
```

---

### 2.2 POST /api/oauth3/login

**Purpose:** Initiate OAuth3 login flow for a specific provider.

**Request:**
```bash
curl -X POST http://localhost:9223/api/oauth3/login \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "gmail",
    "headless": false,
    "popup_timeout_seconds": 120,
    "consent_once": true
  }'
```

**Parameters:**
- `provider_id` (required): "gmail", "linkedin", "github", "twitter", "slack", "discord"
- `headless` (optional, default: false): If true, run in headless mode (for cloud)
- `popup_timeout_seconds` (optional, default: 120): Timeout for OAuth consent popup
- `consent_once` (optional, default: true): If true, only request new scopes not already granted

**Flow (sequence):**

1. Browser navigates to `login_url` for the provider
2. User enters credentials (if not cached) + approves scopes
3. OAuth provider redirects to `redirect_uri` (configured per provider)
4. Extract authorization code from redirect URL
5. Exchange code for access + refresh tokens (backend)
6. Store tokens in encrypted `artifacts/oauth3_tokens.json`
7. Log to `artifacts/oauth3/oauth3_audit.jsonl` with event type "oauth3_login_success"
8. Return success response

**Response (200 OK):**
```json
{
  "success": true,
  "provider_id": "gmail",
  "message": "Gmail login successful",
  "token_id": "token_gmail_20260223_abc123",
  "token_preview": "ya29.a0AfH6...REDACTED...8192",
  "scopes_granted": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
  ],
  "scopes_requested": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
  ],
  "expiry": "2026-02-25T10:30:00Z",
  "expiry_human": "in 2 days",
  "timestamp": "2026-02-23T14:52:30Z"
}
```

**Error (400 Bad Request - user cancelled):**
```json
{
  "success": false,
  "provider_id": "gmail",
  "error": "User cancelled OAuth consent flow",
  "error_code": "USER_CANCELLED",
  "timestamp": "2026-02-23T14:52:40Z"
}
```

**Error (400 Bad Request - timeout):**
```json
{
  "success": false,
  "provider_id": "gmail",
  "error": "OAuth popup timeout after 120 seconds",
  "error_code": "POPUP_TIMEOUT",
  "hint": "Check browser network, OAuth provider may be slow",
  "timestamp": "2026-02-23T14:54:30Z"
}
```

---

### 2.3 GET /api/oauth3/session

**Purpose:** Get current OAuth3 session status (aggregated across all providers).

**Request:**
```bash
curl http://localhost:9223/api/oauth3/session
```

**Response (200 OK):**
```json
{
  "success": true,
  "session_id": "session_20260223_phuc",
  "providers_authenticated": ["gmail", "slack"],
  "providers_expired": ["github", "twitter"],
  "providers_needs_refresh": [],
  "providers_not_logged_in": ["linkedin", "discord"],
  "total_tokens": 4,
  "tokens_by_provider": {
    "gmail": {
      "token_id": "token_gmail_20260223_abc123",
      "status": "valid",
      "expiry": "2026-02-25T10:30:00Z",
      "scopes": [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.readonly"
      ],
      "issued_at": "2026-02-23T10:30:00Z"
    },
    "slack": {
      "token_id": "token_slack_20260223_def456",
      "status": "valid",
      "expiry": "2026-02-25T12:00:00Z",
      "scopes": ["chat:write", "users:read"],
      "issued_at": "2026-02-23T11:00:00Z"
    },
    "github": {
      "token_id": "token_github_20260211_xyz789",
      "status": "expired",
      "expiry": "2026-02-11T14:30:00Z",
      "scopes": ["repo", "user:email"],
      "issued_at": "2026-02-10T14:30:00Z"
    },
    "twitter": {
      "token_id": "token_twitter_20260217_ghi789",
      "status": "expired",
      "expiry": "2026-02-17T16:00:00Z",
      "scopes": ["tweet.read", "users.read"],
      "issued_at": "2026-02-16T16:00:00Z"
    }
  },
  "session_file_path": "artifacts/solace_session.json",
  "tokens_file_path": "artifacts/oauth3_tokens.json",
  "encryption_enabled": true,
  "last_modified": "2026-02-23T14:52:30Z",
  "timestamp": "2026-02-23T14:54:45Z"
}
```

---

### 2.4 POST /api/oauth3/logout

**Purpose:** Logout from a specific OAuth3 provider.

**Request:**
```bash
curl -X POST http://localhost:9223/api/oauth3/logout \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "gmail",
    "revoke_cloud": true,
    "clear_cookies": true
  }'
```

**Parameters:**
- `provider_id` (required): Provider to logout from
- `revoke_cloud` (optional, default: true): If true, also revoke token server-side
- `clear_cookies` (optional, default: true): If true, clear cookies for this provider

**Flow:**

1. Load token from `artifacts/oauth3_tokens.json`
2. If `revoke_cloud=true`, call provider's token revocation endpoint
3. Mark token as revoked in token store
4. Clear localStorage keys for this provider
5. Clear browser cookies for this provider's domain
6. Log event to audit trail
7. Return success response

**Response (200 OK):**
```json
{
  "success": true,
  "provider_id": "gmail",
  "message": "Successfully logged out from Gmail",
  "token_revoked": true,
  "token_revocation_timestamp": "2026-02-23T14:55:10Z",
  "cookies_cleared": true,
  "localStorage_cleared": true,
  "sessionStorage_cleared": true,
  "timestamp": "2026-02-23T14:55:10Z"
}
```

**Error (404 Not Found):**
```json
{
  "success": false,
  "provider_id": "gmail",
  "error": "No active session for this provider",
  "error_code": "NO_ACTIVE_SESSION",
  "timestamp": "2026-02-23T14:55:15Z"
}
```

---

### 2.5 POST /api/oauth3/quick-action

**Purpose:** Execute a pre-built recipe action for an OAuth3 provider.

**Request:**
```bash
curl -X POST http://localhost:9223/api/oauth3/quick-action \
  -H "Content-Type: application/json" \
  -d '{
    "provider_id": "gmail",
    "action_name": "check_unread",
    "options": {
      "limit": 10,
      "include_body": false
    }
  }'
```

**Parameters:**
- `provider_id` (required): Provider ID
- `action_name` (required): Pre-defined action name (see table below)
- `options` (optional): Action-specific parameters

**Supported actions by provider:**

| Provider | Action Name | Recipe ID | Params |
|----------|-------------|-----------|--------|
| gmail | check_unread | gmail_check_unread_v1 | limit, include_body |
| gmail | compose_draft | gmail_compose_draft_v1 | to, subject, body |
| gmail | send_email | gmail_send_v1 | to, subject, body, attachments |
| linkedin | check_dms | linkedin_check_dms_v1 | limit |
| linkedin | view_profile | linkedin_view_profile_v1 | profile_id |
| linkedin | post_update | linkedin_post_v1 | text, image_url |
| github | list_issues | github_list_issues_v1 | repo, state, limit |
| github | list_prs | github_list_prs_v1 | repo, state, limit |
| github | create_issue | github_create_issue_v1 | repo, title, body |
| twitter | view_feed | twitter_view_feed_v1 | limit |
| twitter | post_tweet | twitter_post_v1 | text, media_ids |
| twitter | like_tweet | twitter_like_v1 | tweet_id |
| slack | check_dms | slack_check_dms_v1 | limit |
| slack | list_channels | slack_list_channels_v1 | limit |
| slack | send_message | slack_send_message_v1 | channel_id, text |
| discord | check_dms | discord_check_dms_v1 | limit |
| discord | list_servers | discord_list_servers_v1 | limit |
| discord | send_message | discord_send_message_v1 | channel_id, text |

**Response (200 OK - cache hit):**
```json
{
  "success": true,
  "provider_id": "gmail",
  "action_name": "check_unread",
  "result": {
    "messages": [
      {
        "id": "msg_1",
        "from": "boss@company.com",
        "subject": "Q1 planning meeting",
        "snippet": "Need to discuss Q1 roadmap...",
        "date": "2026-02-23T14:30:00Z"
      },
      {
        "id": "msg_2",
        "from": "friend@gmail.com",
        "subject": "Coffee this weekend?",
        "snippet": "Are you free Saturday?",
        "date": "2026-02-23T12:15:00Z"
      }
    ],
    "unread_count": 2,
    "total_count": 47
  },
  "execution_time_ms": 1240,
  "cache_hit": true,
  "recipe_version": "1.0.0",
  "timestamp": "2026-02-23T14:55:30Z"
}
```

**Response (200 OK - cache miss, LLM generated):**
```json
{
  "success": true,
  "provider_id": "github",
  "action_name": "list_issues",
  "result": {
    "issues": [
      {
        "id": 1,
        "title": "Fix login bug",
        "state": "open",
        "created_at": "2026-02-15T10:00:00Z",
        "updated_at": "2026-02-23T13:45:00Z"
      }
    ],
    "total_count": 12,
    "open_count": 8
  },
  "execution_time_ms": 3450,
  "cache_hit": false,
  "cache_miss_reason": "new_action_variant",
  "recipe_generated": true,
  "recipe_id": "github_list_issues_v1_20260223",
  "timestamp": "2026-02-23T14:55:40Z"
}
```

**Error (401 Unauthorized - token expired):**
```json
{
  "success": false,
  "provider_id": "gmail",
  "error": "Token expired, please login again",
  "error_code": "TOKEN_EXPIRED",
  "action_name": "check_unread",
  "recovery": "POST /api/oauth3/login with provider_id=gmail",
  "timestamp": "2026-02-23T14:55:50Z"
}
```

---

### 2.6 GET /api/oauth3/recipe-status

**Purpose:** Get recipe execution status across all providers.

**Request:**
```bash
curl http://localhost:9223/api/oauth3/recipe-status
```

**Response (200 OK):**
```json
{
  "success": true,
  "running_recipes": [
    {
      "recipe_id": "gmail_check_unread_v1",
      "provider_id": "gmail",
      "action_name": "check_unread",
      "start_time": "2026-02-23T14:55:20Z",
      "progress_percent": 45,
      "status": "executing_query"
    }
  ],
  "queued_recipes": [],
  "completed_recipes": [
    {
      "recipe_id": "linkedin_check_dms_v1",
      "provider_id": "linkedin",
      "action_name": "check_dms",
      "start_time": "2026-02-23T14:54:00Z",
      "end_time": "2026-02-23T14:54:45Z",
      "duration_seconds": 45,
      "status": "success",
      "cache_hit": true
    },
    {
      "recipe_id": "github_list_issues_v1",
      "provider_id": "github",
      "action_name": "list_issues",
      "start_time": "2026-02-23T14:52:00Z",
      "end_time": "2026-02-23T14:53:30Z",
      "duration_seconds": 90,
      "status": "failed",
      "error": "Token expired",
      "cache_hit": false
    }
  ],
  "failed_recipes": [
    {
      "recipe_id": "github_list_issues_v1",
      "provider_id": "github",
      "failure_reason": "Token expired",
      "failure_timestamp": "2026-02-23T14:53:30Z"
    }
  ],
  "summary": {
    "running_count": 1,
    "queued_count": 0,
    "completed_count": 2,
    "failed_count": 1,
    "total_executed": 3,
    "success_rate_percent": 66.67,
    "cache_hit_rate_percent": 50.0
  },
  "timestamp": "2026-02-23T14:55:50Z"
}
```

---

## PART 3: TOKEN STORAGE SCHEMA

### 3.1 Encrypted Token File Structure

**File location:** `artifacts/oauth3_tokens.json` (AES-256-GCM encrypted)

**Decrypted content structure:**

```json
{
  "version": "1.0.0",
  "encryption": {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2",
    "key_iterations": 100000,
    "salt_hex": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
    "nonce_hex": "f0e1d2c3b4a59687",
    "auth_tag_hex": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d"
  },
  "tokens": {
    "gmail": {
      "token_id": "token_gmail_20260223_abc123",
      "provider_id": "gmail",
      "access_token": "ya29.a0AfH6SMBxY8KZj...",
      "refresh_token": "1//0gW-Pu8...",
      "token_type": "Bearer",
      "expiry": "2026-02-25T10:30:00Z",
      "issued_at": "2026-02-23T10:30:00Z",
      "expires_in_seconds": 172800,
      "scopes": [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify"
      ],
      "user_id": "user_123456",
      "user_email": "user@gmail.com",
      "last_action": "read_message",
      "last_action_time": "2026-02-23T14:52:30Z",
      "last_refresh_time": "2026-02-23T10:30:00Z",
      "revoked_at": null,
      "revocation_reason": null,
      "metadata": {
        "client_id": "oauth3_client_id",
        "client_secret_hash": "sha256_hash_of_client_secret",
        "consent_granted_at": "2026-02-23T10:25:00Z",
        "consent_ip": "192.168.1.100",
        "consent_user_agent": "Mozilla/5.0..."
      }
    },
    "linkedin": {
      "token_id": "token_linkedin_20260223_def456",
      "provider_id": "linkedin",
      "access_token": "AQG5rQeWZ1s...",
      "refresh_token": null,
      "token_type": "Bearer",
      "expiry": "2026-02-25T12:00:00Z",
      "issued_at": "2026-02-23T11:00:00Z",
      "expires_in_seconds": 172800,
      "scopes": [
        "r_liteprofile",
        "r_emailaddress",
        "w_member_social"
      ],
      "user_id": "user_789",
      "user_email": "user@example.com",
      "last_action": "post_update",
      "last_action_time": "2026-02-23T14:30:00Z",
      "last_refresh_time": null,
      "revoked_at": null,
      "revocation_reason": null,
      "metadata": {
        "client_id": "linkedin_client_id",
        "consent_granted_at": "2026-02-23T10:55:00Z"
      }
    },
    "github": {
      "token_id": "token_github_20260211_xyz789",
      "provider_id": "github",
      "access_token": "ghp_abc123xyz...",
      "refresh_token": null,
      "token_type": "Bearer",
      "expiry": "2026-02-11T14:30:00Z",
      "issued_at": "2026-02-10T14:30:00Z",
      "expires_in_seconds": -1036800,
      "scopes": ["repo", "user:email"],
      "user_id": "github_user_123",
      "user_email": "user@github.com",
      "last_action": "view_issues",
      "last_action_time": "2026-02-11T14:35:00Z",
      "last_refresh_time": null,
      "revoked_at": null,
      "revocation_reason": null,
      "metadata": {
        "client_id": "github_oauth_app_id",
        "consent_granted_at": "2026-02-10T14:25:00Z"
      }
    }
  },
  "metadata": {
    "created_at": "2026-02-23T09:00:00Z",
    "last_modified": "2026-02-23T14:52:30Z",
    "file_format_version": "1.0.0",
    "browser_version": "solace_1.4.0",
    "hostname": "phuc-laptop",
    "checksum_sha256": "a1b2c3d4e5f6..."
  }
}
```

### 3.2 Token Refresh Strategy

**Automatic refresh triggers:**

```python
def check_and_refresh_tokens():
    """
    Runs every 30 seconds (configurable).
    Refreshes tokens expiring within 5 minutes.
    """
    tokens = load_tokens()
    now = datetime.now(timezone.utc)

    for provider_id, token in tokens.items():
        if token.refresh_token is None:
            continue  # Can't refresh without refresh_token

        expiry = parse_iso8601(token.expiry)
        ttl_seconds = (expiry - now).total_seconds()

        if ttl_seconds < 300:  # 5 minutes
            try:
                new_token = refresh_token_for_provider(provider_id, token.refresh_token)
                tokens[provider_id] = new_token
                log_refresh_event(provider_id, "success")
            except Exception as e:
                log_refresh_event(provider_id, "failed", str(e))

    save_tokens(tokens)
```

**Manual refresh endpoint (Phase 2):**

```
POST /api/oauth3/refresh-token
{
  "provider_id": "gmail"
}

Response:
{
  "success": true,
  "provider_id": "gmail",
  "new_expiry": "2026-02-25T10:30:00Z",
  "refresh_timestamp": "2026-02-23T14:55:50Z"
}
```

### 3.3 Audit Trail Schema

**File location:** `artifacts/oauth3/oauth3_audit.jsonl` (append-only, one JSON object per line)

**Audit entry structure:**

```json
{
  "event_id": "evt_20260223_phuc_001",
  "event_type": "oauth3_login_success",
  "timestamp": "2026-02-23T10:30:00Z",
  "provider_id": "gmail",
  "token_id": "token_gmail_20260223_abc123",
  "user_id": "user_123456",
  "user_email": "user@gmail.com",
  "scopes_requested": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
  ],
  "scopes_granted": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify"
  ],
  "result": "success",
  "session_id": "session_20260223_phuc",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
  "metadata": {
    "browser_uptime_seconds": 180,
    "total_requests_before": 5,
    "oauth_provider_response_time_ms": 1240
  }
}
```

**Audit event types:**

| Event Type | Trigger | Fields |
|------------|---------|--------|
| oauth3_login_success | User completes OAuth flow | scopes_granted, token_id |
| oauth3_login_failed | OAuth flow fails | failure_reason, scopes_requested |
| oauth3_logout | User logs out | token_id, revoked_server_side |
| oauth3_token_refresh | Token auto-refresh | token_id, new_expiry |
| oauth3_action_executed | Recipe action runs | action_name, recipe_id, cache_hit |
| oauth3_action_failed | Recipe action fails | action_name, recipe_id, error |
| oauth3_step_up_required | Sensitive action needs reauth | action_name, required_scopes |
| oauth3_step_up_success | User completes step-up | action_name, reauth_timestamp |
| oauth3_scope_request | New scopes requested | new_scopes, reason |
| oauth3_revocation | Token revoked server-side | token_id, reason |

---

## PART 4: PROVIDER-SPECIFIC OAUTH FLOW HANDLERS

### 4.1 Gmail OAuth Flow (Google)

**Platform:** Google Workspace
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow with PKCE

```python
class GmailOAuthHandler:
    """Gmail OAuth3 handler using Google OAuth 2.0"""

    CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/gmail"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    REVOKE_URL = "https://oauth2.googleapis.com/revoke"
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify"
    ]

    async def initiate_login(self, page: Page) -> str:
        """
        Start Gmail OAuth flow.
        Returns: authorization_code (extracted from redirect)
        """
        # Generate PKCE challenge
        code_verifier = secrets.token_urlsafe(128)[:128]
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')

        # Build authorization URL
        auth_url = (
            f"{self.AUTH_URL}?"
            f"client_id={self.CLIENT_ID}&"
            f"response_type=code&"
            f"scope={urllib.parse.quote(' '.join(self.SCOPES))}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256&"
            f"prompt=consent&"
            f"access_type=offline"
        )

        # Navigate to auth URL
        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Wait for email input or account selection
        try:
            # Try email field
            await page.fill('input[type="email"]', "user@gmail.com", timeout=5000)
            await page.click('button:has-text("Next")')
            await page.wait_for_timeout(1500)
        except:
            pass  # May skip if already logged in

        try:
            # Try password field
            await page.fill('input[type="password"]', os.getenv("GMAIL_PASSWORD"), timeout=5000)
            await page.click('button:has-text("Next")')
            await page.wait_for_timeout(2000)
        except:
            pass  # May skip if already logged in

        # Wait for consent screen
        await page.wait_for_selector('button:has-text("Continue")', timeout=30000)
        await page.click('button:has-text("Continue")')

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract authorization code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, code_verifier

    async def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        """Exchange authorization code for access + refresh tokens"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                json={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.REDIRECT_URI,
                    "code_verifier": code_verifier,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token using refresh token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                json={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token refresh failed: {resp.status}")
                return await resp.json()

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke access token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_URL,
                params={"token": access_token}
            ) as resp:
                return resp.status == 200
```

### 4.2 LinkedIn OAuth Flow

**Platform:** LinkedIn Professional Network
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow

```python
class LinkedInOAuthHandler:
    """LinkedIn OAuth handler"""

    CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
    CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/linkedin"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    REVOKE_URL = "https://api.linkedin.com/v2/me/clientApplicationPermissions"
    SCOPES = [
        "r_liteprofile",
        "r_emailaddress",
        "w_member_social",
    ]

    async def initiate_login(self, page: Page, state: str = None) -> str:
        """Start LinkedIn OAuth flow"""
        if state is None:
            state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.AUTH_URL}?"
            f"response_type=code&"
            f"client_id={self.CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"scope={urllib.parse.quote(' '.join(self.SCOPES))}&"
            f"state={state}"
        )

        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Fill email
        try:
            await page.fill('#username', "user@example.com", timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        # Fill password
        try:
            await page.fill('#password', os.getenv("LINKEDIN_PASSWORD"), timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        # Click login button
        try:
            await page.click('button[aria-label="Sign in"]')
            await page.wait_for_timeout(3000)
        except:
            pass

        # Handle permission request (if present)
        try:
            await page.wait_for_selector('button:has-text("Allow")', timeout=10000)
            await page.click('button:has-text("Allow")')
        except:
            pass

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange code for token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.REDIRECT_URI,
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """LinkedIn doesn't support refresh tokens; raise error"""
        raise NotImplementedError("LinkedIn OAuth does not support refresh tokens")

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                self.REVOKE_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            ) as resp:
                return resp.status in [200, 204]
```

### 4.3 GitHub OAuth Flow

**Platform:** GitHub Developer
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow

```python
class GitHubOAuthHandler:
    """GitHub OAuth handler"""

    CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/github"
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    REVOKE_URL = "https://api.github.com/applications/{client_id}/grants/{access_token}"
    SCOPES = ["repo", "user:email"]

    async def initiate_login(self, page: Page, state: str = None) -> str:
        """Start GitHub OAuth flow"""
        if state is None:
            state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.AUTH_URL}?"
            f"client_id={self.CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"scope={urllib.parse.quote(','.join(self.SCOPES))}&"
            f"state={state}&"
            f"allow_signup=true"
        )

        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Try username field
        try:
            await page.fill('#login_field', "username", timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        # Try password field
        try:
            await page.fill('#password', os.getenv("GITHUB_PASSWORD"), timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        # Click sign in
        try:
            await page.click('input[value="Sign in"]')
            await page.wait_for_timeout(2000)
        except:
            pass

        # Handle 2FA if needed
        try:
            otp_input = page.locator('#otp')
            if await otp_input.is_visible():
                # Would need 2FA code from user
                print("2FA required; user must enter code manually")
                await page.wait_for_url(f"**/oauth/callback/**", timeout=60000)
        except:
            pass

        # Wait for authorization page and confirm
        try:
            await page.wait_for_selector('button:has-text("Authorize")', timeout=10000)
            await page.click('button:has-text("Authorize")')
        except:
            pass

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange code for token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                json={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": self.REDIRECT_URI,
                },
                headers={"Accept": "application/json"}
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """GitHub doesn't support refresh tokens; raise error"""
        raise NotImplementedError("GitHub OAuth does not support refresh tokens")

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                self.REVOKE_URL.format(
                    client_id=self.CLIENT_ID,
                    access_token=access_token
                ),
                auth=aiohttp.BasicAuth(self.CLIENT_ID, self.CLIENT_SECRET)
            ) as resp:
                return resp.status in [204, 404]  # 404 means already revoked
```

### 4.4 Twitter/X OAuth Flow

**Platform:** X (formerly Twitter)
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow with PKCE

```python
class TwitterOAuthHandler:
    """Twitter/X OAuth handler"""

    CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
    CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/twitter"
    AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"
    SCOPES = ["tweet.read", "users.read", "tweet.write"]

    async def initiate_login(self, page: Page) -> str:
        """Start Twitter OAuth flow"""
        code_verifier = secrets.token_urlsafe(128)[:128]
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')

        state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.AUTH_URL}?"
            f"response_type=code&"
            f"client_id={self.CLIENT_ID}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"scope={urllib.parse.quote(' '.join(self.SCOPES))}&"
            f"state={state}&"
            f"code_challenge={code_challenge}&"
            f"code_challenge_method=S256"
        )

        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Handle login flow
        try:
            # Try phone/email field
            await page.fill('input[autocomplete="username"]', "user@example.com", timeout=5000)
            await page.click('button:has-text("Next")')
            await page.wait_for_timeout(1500)
        except:
            pass

        try:
            # Try password field
            await page.fill('input[type="password"]', os.getenv("TWITTER_PASSWORD"), timeout=5000)
            await page.click('button:has-text("Log in")')
            await page.wait_for_timeout(2000)
        except:
            pass

        # Handle permission screen
        try:
            await page.wait_for_selector('a[href*="authorize"]', timeout=10000)
            await page.click('a:has-text("Authorize app")')
        except:
            try:
                await page.wait_for_selector('button:has-text("Authorize")', timeout=10000)
                await page.click('button:has-text("Authorize")')
            except:
                pass

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, code_verifier

    async def exchange_code_for_token(self, code: str, code_verifier: str) -> dict:
        """Exchange code for token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                json={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.REDIRECT_URI,
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "code_verifier": code_verifier,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token refresh failed: {resp.status}")
                return await resp.json()

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_URL,
                json={"token": access_token},
                auth=aiohttp.BasicAuth(self.CLIENT_ID, self.CLIENT_SECRET)
            ) as resp:
                return resp.status == 200
```

### 4.5 Slack OAuth Flow

**Platform:** Slack Workspace
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow with workspace selection

```python
class SlackOAuthHandler:
    """Slack OAuth handler"""

    CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/slack"
    AUTH_URL = "https://slack.com/oauth/v2/authorize"
    TOKEN_URL = "https://slack.com/api/oauth.v2.access"
    REVOKE_URL = "https://slack.com/api/auth.revoke"
    SCOPES = ["chat:write", "users:read", "channels:read"]

    async def initiate_login(self, page: Page, workspace: str = None) -> str:
        """Start Slack OAuth flow"""
        state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.AUTH_URL}?"
            f"client_id={self.CLIENT_ID}&"
            f"scope={urllib.parse.quote(','.join(self.SCOPES))}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"state={state}"
        )

        if workspace:
            auth_url += f"&team={workspace}"

        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Handle workspace selection if needed
        try:
            workspace_input = page.locator('input[placeholder*="workspace"]')
            if await workspace_input.is_visible():
                await workspace_input.fill(workspace or "myworkspace")
                await page.click('button:has-text("Continue")')
                await page.wait_for_timeout(1500)
        except:
            pass

        # Handle email/password login
        try:
            await page.fill('input[type="email"]', "user@example.com", timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        try:
            await page.fill('input[type="password"]', os.getenv("SLACK_PASSWORD"), timeout=5000)
            await page.click('button:has-text("Sign In")')
            await page.wait_for_timeout(2000)
        except:
            pass

        # Approve app
        try:
            await page.wait_for_selector('button:has-text("Allow")', timeout=10000)
            await page.click('button:has-text("Allow")')
        except:
            pass

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange code for token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": self.REDIRECT_URI,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str = None) -> dict:
        """Slack tokens don't expire; this is a no-op"""
        raise NotImplementedError("Slack tokens don't expire; refresh not needed")

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_URL,
                data={"token": access_token}
            ) as resp:
                data = await resp.json()
                return data.get("ok", False)
```

### 4.6 Discord OAuth Flow

**Platform:** Discord Developer Portal
**OAuth Version:** OAuth 2.0
**Flow Type:** Authorization Code Flow

```python
class DiscordOAuthHandler:
    """Discord OAuth handler"""

    CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
    CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
    REDIRECT_URI = "http://localhost:9223/oauth/callback/discord"
    AUTH_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    REVOKE_URL = "https://discord.com/api/oauth2/token/revoke"
    SCOPES = ["identify", "email", "guilds", "guilds.members.read"]

    async def initiate_login(self, page: Page, state: str = None) -> str:
        """Start Discord OAuth flow"""
        if state is None:
            state = secrets.token_urlsafe(32)

        auth_url = (
            f"{self.AUTH_URL}?"
            f"client_id={self.CLIENT_ID}&"
            f"response_type=code&"
            f"scope={urllib.parse.quote(' '.join(self.SCOPES))}&"
            f"redirect_uri={urllib.parse.quote(self.REDIRECT_URI)}&"
            f"state={state}&"
            f"prompt=consent"
        )

        await page.goto(auth_url, wait_until="networkidle")
        await page.wait_for_timeout(1000)

        # Handle login
        try:
            await page.fill('input[name="email"]', "user@example.com", timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        try:
            await page.fill('input[type="password"]', os.getenv("DISCORD_PASSWORD"), timeout=5000)
            await page.wait_for_timeout(500)
        except:
            pass

        try:
            await page.click('button:has-text("Log In")')
            await page.wait_for_timeout(2000)
        except:
            pass

        # Handle authorization
        try:
            await page.wait_for_selector('button:has-text("Authorize")', timeout=10000)
            await page.click('button:has-text("Authorize")')
        except:
            pass

        # Wait for redirect
        await page.wait_for_url(f"**/oauth/callback/**", timeout=15000)

        # Extract code
        url = page.url
        code = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("code", [None])[0]

        if not code:
            raise ValueError("No authorization code in redirect URL")

        return code, state

    async def exchange_code_for_token(self, code: str) -> dict:
        """Exchange code for token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.REDIRECT_URI,
                    "scope": " ".join(self.SCOPES),
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token exchange failed: {resp.status}")
                return await resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh access token"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.CLIENT_ID,
                    "client_secret": self.CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
            ) as resp:
                if resp.status != 200:
                    raise ValueError(f"Token refresh failed: {resp.status}")
                return await resp.json()

    async def revoke_token(self, access_token: str) -> bool:
        """Revoke token server-side"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.REVOKE_URL,
                data={"token": access_token},
                auth=aiohttp.BasicAuth(self.CLIENT_ID, self.CLIENT_SECRET)
            ) as resp:
                return resp.status == 200
```

---

## PART 5: IMPLEMENTATION TIMELINE & SPRINT BREAKDOWN

### Sprint 1 (Week 1 – Foundation): 2026-02-24 to 2026-03-02

| Task | Owner | Estimate | Priority |
|------|-------|----------|----------|
| **Homepage HTML/CSS (no build step, vanilla JS)** | Frontend | 2d | P0 |
| Create `browser/homepage.html` (static) | Frontend | 1d | P0 |
| Style with vanilla CSS (Flexbox layout) | Frontend | 0.5d | P0 |
| Add JavaScript event listeners for quick actions | Frontend | 0.5d | P0 |
| **Add GET /api/oauth3/providers endpoint** | Backend | 2d | P0 |
| Create `oauth3_handlers.py` module | Backend | 1d | P0 |
| Implement token status detection logic | Backend | 1d | P0 |
| **Per-provider session tracking** | Backend | 2d | P0 |
| Create `artifacts/oauth3_tokens.json` loader/saver | Backend | 1d | P0 |
| Implement AES-256-GCM encryption/decryption | Backend | 1d | P0 |
| **Add POST /api/oauth3/login handler** | Backend | 3d | P0 |
| Implement generic OAuth code flow | Backend | 1.5d | P0 |
| Add provider-specific handlers (Gmail + LinkedIn) | Backend | 1.5d | P0 |
| Test full login flow end-to-end | QA | 1d | P0 |

**Sprint 1 Success Criteria (Rung 641):**
- Homepage loads at `http://localhost:9223/`
- GET /api/oauth3/providers returns valid JSON with all 6 providers
- POST /api/oauth3/login works for Gmail (end-to-end OAuth flow)
- Tokens encrypted and stored in `artifacts/oauth3_tokens.json`
- Audit log written to `artifacts/oauth3/oauth3_audit.jsonl`

---

### Sprint 2 (Week 2 – Features): 2026-03-03 to 2026-03-09

| Task | Owner | Estimate | Priority |
|------|-------|----------|----------|
| **Add remaining OAuth handlers** | Backend | 2.5d | P0 |
| GitHub OAuth handler | Backend | 0.5d | P0 |
| Twitter OAuth handler | Backend | 0.5d | P0 |
| Slack OAuth handler | Backend | 0.5d | P0 |
| Discord OAuth handler | Backend | 0.5d | P0 |
| LinkedIn OAuth handler (refinement) | Backend | 0.5d | P0 |
| **Add POST /api/oauth3/logout endpoint** | Backend | 1d | P0 |
| Token revocation (per-provider) | Backend | 0.5d | P0 |
| Clear cookies/localStorage | Backend | 0.5d | P0 |
| **Implement token refresh logic** | Backend | 1.5d | P0 |
| Auto-refresh on 5-min expiry threshold | Backend | 1d | P0 |
| Background refresh task (every 30s) | Backend | 0.5d | P0 |
| **Quick-action framework** | Backend | 2d | P0 |
| Create `data/default/recipes/quick_actions.json` config | Backend | 0.5d | P0 |
| POST /api/oauth3/quick-action handler | Backend | 1d | P0 |
| Integrate with recipe engine | Backend | 0.5d | P0 |
| **Add GET /api/oauth3/recipe-status endpoint** | Backend | 1d | P0 |
| Recipe execution status tracking | Backend | 1d | P0 |
| **Integration testing** | QA | 2d | P0 |
| Test all 6 OAuth flows | QA | 1d | P0 |
| Test token refresh + auto-refresh | QA | 1d | P0 |

**Sprint 2 Success Criteria (Rung 641):**
- All 6 OAuth providers can login/logout
- Token refresh works automatically
- Quick-action buttons execute recipes
- Recipe status endpoint returns valid data
- All tests pass

---

### Sprint 3 (Week 3 – Polish): 2026-03-10 to 2026-03-16

| Task | Owner | Estimate | Priority |
|------|-------|----------|----------|
| **Multi-device token sync (encrypted)** | Backend | 2d | P1 |
| AES-256-GCM encryption for cloud sync | Backend | 1d | P1 |
| POST /api/oauth3/sync endpoint | Backend | 1d | P1 |
| **Step-up auth integration** | Backend | 1.5d | P1 |
| Implement step-up challenge flow | Backend | 1d | P1 |
| POST /api/oauth3/step-up endpoint | Backend | 0.5d | P1 |
| **Evidence bundle tracking** | Backend | 1d | P1 |
| Log all OAuth actions to audit trail | Backend | 0.5d | P1 |
| Generate evidence bundle per request | Backend | 0.5d | P1 |
| **Documentation & QA** | Docs+QA | 2d | P1 |
| Write API documentation | Docs | 1d | P1 |
| Full end-to-end testing + bug fixes | QA | 1d | P1 |
| **Security audit** | Security | 1.5d | P1 |
| OWASP Top 10 review | Security | 1d | P1 |
| Credential handling audit | Security | 0.5d | P1 |

**Sprint 3 Success Criteria (Rung 641):**
- Multi-device sync working with AES-256-GCM
- Step-up auth challenges trigger for sensitive actions
- All OAuth actions audited
- Security review passed
- Full documentation written

---

## PART 6: RISK ANALYSIS & MITIGATION

### 6.1 High-Risk Issues

#### Risk #1: OAuth Popup Handling Varies by Provider

**Problem:** Each OAuth provider has unique flows (Gmail vs LinkedIn vs GitHub), making automation fragile.

**Failure Modes:**
- Popup timeout before user approval
- Different form field selectors per provider
- 2FA/MFA interrupting flow (GitHub, Twitter)
- Provider updates form structure → selectors break

**Risk Level:** HIGH

**Mitigation:**
1. **Provider-specific handlers**: Each provider has dedicated handler class (see Section 4)
2. **Selector healing**: Use multiple selectors per form field; try alternatives if first fails
3. **Timeout configuration**: Make timeout configurable per provider (default 120s)
4. **2FA fallback**: For 2FA-required providers (GitHub), pause and wait for manual user interaction
5. **Monitoring**: Log all OAuth flow failures to artifacts/oauth3/oauth3_audit.jsonl with selector name
6. **Test coverage**: Regression tests for each provider (Phase 2)

**Implementation detail:** Wrapped try/catch blocks around each selector interaction; fallback to next selector if timeout

---

#### Risk #2: Token Refresh Fails; Token Becomes Invalid

**Problem:** Some providers don't support refresh tokens (LinkedIn, GitHub); tokens expire and sessions break.

**Failure Modes:**
- Refresh token is null → can't auto-refresh
- Provider revokes token server-side without warning
- Token expiry calculation wrong (time zone issue)

**Risk Level:** HIGH

**Mitigation:**
1. **Provider support matrix**: Document which providers support refresh (Gmail: yes, LinkedIn: no, GitHub: no, Twitter: yes, Slack: no, Discord: yes)
2. **Keep-alive strategy**: For no-refresh providers, issue periodic "ping" action (e.g., check profile) to keep session alive
3. **Explicit expiry checking**: Use provider API to validate token expiry; don't trust local calculation
4. **User notification**: Homepage shows "Needs refresh" status 5 min before expiry; user can click [Refresh]
5. **Revocation detection**: POST /api/oauth3/quick-action checks if token is revoked; returns error with recovery steps

**Implementation detail:** `artifacts/oauth3_tokens.json` has `can_refresh` boolean per provider; auto-refresh only runs if true

---

#### Risk #3: Session Persistence Across Reboots

**Problem:** Browser process dies; cookies/localStorage lost even with artifacts/solace_session.json

**Failure Modes:**
- Cookies not persisted to disk
- localStorage not persisted to disk
- Playwright context not properly saved
- artifacts/solace_session.json corrupted

**Risk Level:** HIGH

**Mitigation:**
1. **Persistent context enabled**: PersistentBrowserServer uses `context=await browser.new_context(storage_state=session_file)`
2. **Autosave every 30s**: Background task saves session state to disk
3. **Encrypt sensitive data**: OAuth tokens stored separately in encrypted `artifacts/oauth3_tokens.json`
4. **Checksum validation**: `artifacts/oauth3_tokens.json` includes SHA256 checksum; corruption detected on load
5. **Manual save endpoint**: POST /api/save-session forces immediate save
6. **Recovery procedure**: If corruption detected, prompt user to re-login

**Implementation detail:** PersistentBrowserServer.__init__ has `autosave_seconds` parameter; defaults to 30

---

### 6.2 Medium-Risk Issues

#### Risk #4: Scope Mismatch Between Client & Provider

**Problem:** Client requests scopes that provider doesn't grant; silent failure.

**Failure Modes:**
- Recipe calls Gmail API with scope "compose" but token only has "read"
- Provider silently doesn't grant requested scope
- Recipe fails with 403 Forbidden

**Risk Level:** MEDIUM

**Mitigation:**
1. **Scope validation on login**: GET /api/oauth3/providers returns scopes_granted vs scopes_requested
2. **Scope registry**: specs/oauth3-scope-registry.json maps provider.action → required_scopes
3. **Recipe declares required scopes**: recipe JSON has `required_scopes: ["..."]` field
4. **Pre-execution gate**: browser-oauth3-gate (skill) checks token has all required scopes before executing recipe
5. **User feedback**: If scopes missing, show prompt: "Re-login with additional scope X?"

**Implementation detail:** Gate 3 (G3_SCOPE_PRESENT) in browser-oauth3-gate.md enforces this

---

#### Risk #5: Encryption Key Management

**Problem:** Where is the AES-256-GCM key stored for encrypting tokens?

**Failure Modes:**
- Key stored in plaintext → credentials exfiltrable
- Key lost → can't decrypt tokens on new machine
- Key compromised → all tokens compromised

**Risk Level:** MEDIUM

**Mitigation:**
1. **Key derivation**: Use PBKDF2(user_password_hash, salt, 100k iterations) to derive key
2. **Salt & nonce storage**: artifacts/oauth3_tokens.json includes salt_hex + nonce_hex (used for derivation)
3. **No plaintext key on disk**: Key never written; derived on-demand from user password
4. **Multi-device sync**: To sync tokens to another machine, user must provide password (re-derive key)
5. **Key rotation**: If user changes password, tokens must be re-encrypted

**Implementation detail:** See token schema section 3.1 — encryption field shows algorithm + derivation params

---

#### Risk #6: Recipe Cache Hit Rate <70%

**Problem:** If cache miss rate > 30%, LLM cost becomes too high (~$0.006 per miss vs ~$0.001 per cached replay)

**Failure Modes:**
- DOM changes on provider website → selector mismatches
- New action type not in cache
- Provider UX redesigned

**Risk Level:** MEDIUM

**Mitigation:**
1. **Recipe versioning**: New recipe versions inherit tests from old versions (never-worse gate)
2. **Selector healing**: If selector fails, recipe tries fallback selectors (built into recipe JSON)
3. **Recipe caching strategy**: Cache key = SHA256(intent + platform + action_type); maximize cache locality
4. **Monitor hit rate**: /api/oauth3/recipe-status returns cache_hit_rate_percent
5. **Automated healing**: When recipe fails, LLM generates new version; tests old version's test cases

**Implementation detail:** See browser-recipe-engine.md section 6 (cache strategy)

---

### 6.3 Low-Risk Issues

#### Risk #7: Homepage JavaScript Errors

**Problem:** Vanilla JS in homepage.html has bugs; page doesn't load.

**Risk Level:** LOW

**Mitigation:**
1. **No build step**: Vanilla JS, no transpilation → easier to debug
2. **Browser console logging**: All errors logged to browser console + server logs
3. **Graceful degradation**: If API endpoint fails, show error message to user
4. **Manual testing**: QA tests homepage on Chrome, Firefox, Safari

---

#### Risk #8: Rate Limiting on OAuth Providers

**Problem:** OAuth providers rate-limit login attempts → account lockout.

**Risk Level:** LOW

**Mitigation:**
1. **Backoff strategy**: If login fails 3x, wait 5 minutes before retrying
2. **Error codes**: Detect rate-limit errors (429) vs auth failures (401)
3. **User feedback**: Show "Too many attempts; try again in 5 minutes"
4. **Monitoring**: Log rate-limit hits to audit trail for diagnostics

---

## PART 7: RECIPE FRAMEWORK HOOKS

### 7.1 Recipe Execution with OAuth3 Token

**Recipe JSON structure (example):**

```json
{
  "recipe_id": "gmail_check_unread_v1",
  "version": "1.0.0",
  "provider_id": "gmail",
  "action_name": "check_unread",
  "description": "Check unread Gmail messages",
  "required_scopes": [
    "https://www.googleapis.com/auth/gmail.readonly"
  ],
  "max_steps": 50,
  "timeout_seconds": 60,
  "portals": [
    {
      "selector": "input[aria-label='Search mail']",
      "role": "textbox",
      "ref_id": "search_box",
      "healing_chain": [
        "input[aria-label='Search mail']",
        "input[placeholder='Search mail']",
        "#search"
      ]
    },
    {
      "selector": "span[aria-label*='unread']",
      "role": "text",
      "ref_id": "unread_count",
      "healing_chain": [
        "span[aria-label*='unread']",
        "span:has-text('unread')",
        ".unread-count"
      ]
    }
  ],
  "execution_trace": [
    {
      "step": 1,
      "action": "navigate",
      "target_url": "https://mail.google.com/mail/u/0/"
    },
    {
      "step": 2,
      "action": "wait_for_element",
      "target_ref": "search_box",
      "timeout_ms": 5000
    },
    {
      "step": 3,
      "action": "click",
      "target_ref": "unread_count"
    },
    {
      "step": 4,
      "action": "screenshot"
    },
    {
      "step": 5,
      "action": "extract_data",
      "data_schema": {
        "messages": [
          {
            "from": "string",
            "subject": "string",
            "snippet": "string",
            "date": "iso8601"
          }
        ]
      }
    }
  ],
  "output_schema": {
    "type": "object",
    "properties": {
      "messages": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "from": {"type": "string"},
            "subject": {"type": "string"},
            "snippet": {"type": "string"},
            "date": {"type": "string", "format": "date-time"}
          }
        }
      },
      "unread_count": {"type": "integer"},
      "total_count": {"type": "integer"}
    }
  },
  "test_cases": [
    {
      "test_id": "gmail_check_unread_t1",
      "description": "Should return list of unread messages",
      "expected_output": {
        "messages": [{"from": "test@example.com", "subject": "Test message"}],
        "unread_count": 1
      }
    }
  ]
}
```

### 7.2 Recipe Execution Flow (with OAuth3 gates)

```
User request: POST /api/oauth3/quick-action
  ↓
1. Load OAuth3 token for provider_id
  ↓
2. Run browser-oauth3-gate (4 gates):
   G1: Token exists? YES → continue
   G2: Token expired? NO → continue
   G3: Required scopes in token? YES → continue
   G4: Step-up needed? (for destructive actions) NO → continue
  ↓
3. If any gate fails → BLOCKED + return error
  ↓
4. Cache lookup: SHA256(intent + platform + action_type)
  ↓
5. Cache HIT:
   → Load recipe from cache
   → Execute recipe step-by-step
   → Log each step to execution_trace
   → Validate output against output_schema
   → Return result + cache_hit=true
  ↓
5b. Cache MISS:
   → Call LLM to generate new recipe
   → Validate recipe syntax + scopes
   → Test recipe against test_cases
   → Cache new recipe
   → Execute recipe
   → Return result + cache_hit=false
  ↓
6. Post-execution:
   → Update last_action + last_action_time in token store
   → Log event to artifacts/oauth3/oauth3_audit.jsonl
   → Return result to user
```

### 7.3 OAuth3 Token Access from Recipe Engine

**Python API (recipe engine calls this):**

```python
from oauth3 import AgencyToken, load_token, get_token_scopes, is_expired

# Inside recipe execution handler
async def execute_recipe(provider_id: str, recipe: Recipe) -> dict:
    """Execute a recipe with OAuth3 enforcement"""

    # Load token
    token: AgencyToken = load_token(provider_id)

    if token is None:
        raise Exception(f"No token for provider {provider_id}")

    # Enforce gates
    if is_expired(token):
        raise Exception(f"Token expired for {provider_id}")

    scopes_needed = recipe.required_scopes
    scopes_available = get_token_scopes(token)
    scopes_missing = set(scopes_needed) - set(scopes_available)

    if scopes_missing:
        raise Exception(f"Missing scopes: {scopes_missing}")

    # Execute recipe steps
    for step in recipe.execution_trace:
        if step.action == "navigate":
            # Browser-specific action
            await browser.page.goto(step.target_url)
        elif step.action == "api_call":
            # API-specific action (use OAuth token as Bearer)
            headers = {"Authorization": f"Bearer {token.access_token}"}
            response = await api_call(step.api_method, headers=headers)
        # ... more actions ...

    # Log execution
    log_oauth_action(
        event_type="oauth3_action_executed",
        provider_id=provider_id,
        action_name=recipe.action_name,
        recipe_id=recipe.recipe_id,
        scopes_used=scopes_needed,
        result="success"
    )

    return result
```

---

## PART 8: GLOSSARY & ABBREVIATIONS

| Term | Definition |
|------|-----------|
| **OAuth3** | Extended OAuth 2.0 with step-up auth, consent UI, revocation |
| **Token ID** | Unique identifier for an OAuth token; used in audit logs |
| **TTL** | Time-to-live (seconds until token expires) |
| **Refresh token** | Long-lived credential used to obtain new access tokens |
| **Scope** | Named permission (e.g., "gmail.modify"); atomic unit of authorization |
| **Step-up auth** | Additional authorization challenge for sensitive actions |
| **Provider** | OAuth service (Gmail, LinkedIn, GitHub, Twitter, Slack, Discord) |
| **Recipe** | Versioned, deterministic automation script for a specific action |
| **Cache hit** | Recipe found in cache; no LLM call needed |
| **Cache miss** | Recipe not in cache; LLM generates new recipe |
| **Portal** | Recipe element targeting entry (selector + healing chain) |
| **Evidence bundle** | Audit record of an action + test results |

---

## PART 9: ACCEPTANCE CRITERIA (Rung 641)

### Sprint 1 Completion (Foundation Phase)

- [ ] Homepage HTML loads without errors at `http://localhost:9223/`
- [ ] GET /api/oauth3/providers returns JSON with all 6 providers + status icons
- [ ] POST /api/oauth3/login works end-to-end for Gmail
- [ ] Tokens encrypted and stored in `artifacts/oauth3_tokens.json`
- [ ] Audit log entries written to `artifacts/oauth3/oauth3_audit.jsonl`
- [ ] Token status logic correctly determines: authenticated, expired, not_logged_in
- [ ] Playwright persistent context maintains login across browser restart

### Sprint 2 Completion (Features Phase)

- [ ] All 6 OAuth providers (Gmail, LinkedIn, GitHub, Twitter, Slack, Discord) can login/logout
- [ ] Token refresh works automatically (every 30s, checks 5-min expiry threshold)
- [ ] Quick-action buttons trigger recipes via POST /api/oauth3/quick-action
- [ ] GET /api/oauth3/recipe-status returns valid running/completed/failed lists
- [ ] POST /api/oauth3/logout successfully revokes tokens server-side
- [ ] GET /api/oauth3/session aggregates all provider statuses correctly
- [ ] All unit tests pass (OAuth handlers, token encryption, audit logging)

### Sprint 3 Completion (Polish Phase)

- [ ] Multi-device token sync works with AES-256-GCM encryption
- [ ] Step-up auth flow triggers for destructive actions (delete, publish, etc.)
- [ ] Evidence bundles generated for every OAuth action
- [ ] Security audit completed; no OWASP Top 10 vulnerabilities
- [ ] API documentation complete (all endpoints, request/response examples)
- [ ] Homepage shows session info: uptime, API call count, storage size
- [ ] Recipe cache hit rate ≥ 70% for common actions

---

## CONCLUSION

This architecture provides a **deterministic, auditable, provider-agnostic OAuth3 portal** for the Solace Browser. The design emphasizes:

1. **Session persistence**: Tokens stored locally with encryption; browser survives reboots
2. **Recipe integration**: OAuth3 gates enforce scopes before recipe execution
3. **Evidence tracking**: Every action logged to audit trail for compliance
4. **Provider flexibility**: Handler-based design allows easy addition of new OAuth providers
5. **User control**: Clear status indicators + one-click logout per provider

The phased rollout (Sprint 1→2→3) ensures a solid foundation before adding advanced features.

**Rung Target: 641** ✅ All design decisions are deterministic, testable, and well-scoped.

---

## PART 10: WEB APP MODE + ACTIVITY DATATABLE + CAPTURE SETTINGS

### 10.1 Feasibility

Yes — this is directly feasible with the current Solace Browser stack.
The existing UI server (`ui_server.py`) can serve a full web app homepage and route detail pages.
No architecture rewrite is required; this is an additive feature set.

### 10.2 Web App Homepage Model

Homepage sections:

1. Compatible Sites Grid
2. OAuth3 token/session status cards
3. Recent Activity table (DataTables.js)
4. Capture mode controls (Screenshot / Full Archive / Both)

DataTables columns (minimum):

- `timestamp_utc`
- `site`
- `recipe_id`
- `pages_clicked`
- `actions_count`
- `duration_ms`
- `capture_mode`
- `result`
- `details_link`

### 10.3 Interaction Detail Page

Route: `GET /activity/{activity_id}`

Required detail view payload:

- full action trace (ordered step list)
- URL transitions
- selector/action per step
- screenshot links (if captured)
- full-page HTML archive link (if captured)
- audit hash chain fields (`entry_hash`, `prev_hash`)

UI behavior:

- clicking a row opens detail page
- screenshot opens modal preview
- HTML archive opens in new tab or modal (read-only)

### 10.4 Capture Settings (Part 11 Modes)

Add runtime setting:

```json
{
  "part11_enabled": true,
  "capture_mode": "screenshot | archive | both",
  "audit_dir": "artifacts/part11",
  "archive_compression": "none | pzip"
}
```

Mode semantics:

- `screenshot`: store PNG evidence only
- `archive`: store full-page package (HTML/CSS/JS/assets)
- `both`: store both evidence sets per event

### 10.5 API Additions

```http
GET  /api/activity?site=&from=&to=&limit=
GET  /api/activity/{activity_id}
GET  /api/activity/{activity_id}/screenshot
GET  /api/activity/{activity_id}/archive
GET  /api/settings/capture
POST /api/settings/capture
```

`POST /api/settings/capture` request:

```json
{
  "part11_enabled": true,
  "capture_mode": "both",
  "audit_dir": "artifacts/part11",
  "archive_compression": "pzip"
}
```

### 10.6 Storage Schema (Minimal)

`artifacts/activity_log.jsonl`:

```json
{
  "activity_id": "act_20260225_001",
  "timestamp_utc": "2026-02-25T02:10:00Z",
  "site": "gmail",
  "recipe_id": "gmail-read-inbox",
  "pages_clicked": 7,
  "actions_count": 18,
  "duration_ms": 12450,
  "capture_mode": "both",
  "screenshot_path": "artifacts/part11/.../evidence.png",
  "archive_path": "artifacts/part11/.../archive/index.html",
  "result": "success",
  "entry_hash": "sha256:...",
  "prev_hash": "sha256:..."
}
```

### 10.7 Implementation Plan (Incremental)

1. Add capture settings API + persistence.
2. Add activity log writer on every recipe execution.
3. Add `/activity` list and detail endpoints.
4. Render DataTables homepage section.
5. Add screenshot/archive modal interactions.
6. Add regression tests for all three capture modes.

### 10.8 Acceptance Criteria (Extension)

- [ ] `capture_mode` can be switched at runtime (`screenshot|archive|both`)
- [ ] Activity table renders last 100 actions with filters
- [ ] Clicking row opens deterministic detail page
- [ ] Screenshot modal works for screenshot/both modes
- [ ] Archive link works for archive/both modes
- [ ] Audit chain fields present for every logged activity

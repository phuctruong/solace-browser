<!-- Diagram: hub-oauth3-keepalive -->
# hub-oauth3-keepalive: OAuth3 Session Keep-Alive
# DNA: `keepalive = monitor(cookies) × ping(domain) × refresh(session) → evidence(alive|expired)`
# Auth: 65537 | State: GOOD | Version: 1.1.0

## Extends
- [hub-oauth3](hub-oauth3.prime-mermaid.md) — parent diagram

## Design

OAuth3 keep-alive ensures domain sessions stay active so AI workers can
operate without re-authentication. The browser owns the cookies — we
monitor and refresh them.

## Canonical Diagram

```mermaid
flowchart TB
    subgraph MONITOR[Session Monitor — per domain]
        CHECK_COOKIES[Check domain cookies<br>via browser cookie API]
        CHECK_COOKIES -->|cookies exist| PING[Ping domain endpoint<br>lightweight GET request]
        CHECK_COOKIES -->|no cookies| EXPIRED[Session Expired]
        PING -->|200 OK| ALIVE[Session Active<br>update last_verified]
        PING -->|401/403| EXPIRED
        PING -->|network error| RETRY[Retry in 30s]
    end

    subgraph SIDEBAR[Yinyang Sidebar Display]
        ALIVE --> SHOW_GREEN[Green dot<br>"Signed in"]
        EXPIRED --> SHOW_RED[Red dot<br>"Sign in needed"]
        SHOW_RED --> CTA_LOGIN[CTA: Sign in to {domain}]
    end

    subgraph KEEPALIVE[Keep-Alive Loop]
        CRON[Every 15 minutes] --> CHECK_COOKIES
        NAVIGATE[On domain navigate] --> CHECK_COOKIES
        WORKER_START[Before worker run] --> CHECK_COOKIES
    end

    subgraph EVIDENCE[Evidence Trail]
        ALIVE --> LOG_ALIVE[Log: session_alive<br>domain + timestamp + cookie_count]
        EXPIRED --> LOG_EXPIRED[Log: session_expired<br>domain + timestamp + reason]
    end
```

## Per-Domain Session State

Each domain the user has logged into gets tracked:
```json
{
  "domain": "mail.google.com",
  "status": "active|expired|unknown",
  "last_verified": "2026-03-22T12:00:00Z",
  "cookie_count": 12,
  "session_age_hours": 4.5,
  "keep_alive_enabled": true
}
```

## Sidebar Display (in domain_detected mode)

When viewing a domain with OAuth3 status:
```
┌──────────────────────────────┐
│ 🟢 mail.google.com  5 apps  │  ← green = session active
│ Signed in · 4h ago          │  ← last verified
├──────────────────────────────┤
│ ★ Gmail Inbox Triage  [Run] │  ← highlighted (url_match)
│ ★ Gmail Spam Cleaner  [Run] │  ← highlighted
│   Gmail Draft Writer   [Run] │  ← not highlighted
└──────────────────────────────┘
```

When session expired:
```
┌──────────────────────────────┐
│ 🔴 mail.google.com  5 apps  │  ← red = expired
│ Sign in needed               │  ← CTA
├──────────────────────────────┤
│   Gmail Inbox Triage  [Run] │  ← all dimmed
│   ...                        │
└──────────────────────────────┘
```

## Implementation

The Hub cron service manages keep-alive as a first-class concern. Each app
manifest can declare `keep_alive` settings:

```yaml
# In manifest.yaml
keep_alive:
  enabled: true
  interval: 15m          # How often to ping
  action: navigate       # navigate | read_page | api_call
  url: "https://mail.google.com/mail/u/0/#inbox"
  evidence: true         # Log keep-alive events
```

**Cron-driven keep-alive loop:**
1. Hub cron scans all apps for `keep_alive.enabled=true`
2. Every `interval`, it runs a lightweight action (navigate to page, read inbox)
3. This keeps cookies fresh and sessions alive
4. Between scheduled worker runs, keep-alive fills the gaps
5. Evidence is recorded: domain, timestamp, action, result

**Architecture:**
1. App manifests declare `keep_alive` settings
2. Hub cron service (`/api/schedules`) includes keep-alive jobs alongside worker schedules
3. Runtime API: `GET /api/v1/oauth3/domain/{domain}` returns session status
4. Sidebar shows auth status with green/red dot in domain_detected mode
5. Workers check session status before running — fail-fast if expired
6. C++ tab reporter tracks cookie freshness per domain

## PM Status
<!-- Updated: 2026-03-23 | Session: P-76 -->
| Node | Status | Evidence |
|------|--------|----------|
| CHECK_COOKIES | GOOD | C++ SolaceTabUrlReporter writes domain_auth.json, GET /api/v1/domains/:domain/status returns oauth3_status |
| PING | GOOD | GET /api/v1/browser/current-url detects logged_in state via URL redirect tracking |
| SIDEBAR | PENDING | Sidebar v2 shows domain_detected mode but keep-alive dots not wired |
| KEEPALIVE | PENDING | Cron scheduler exists (9 schedules) but keep-alive jobs not auto-created from manifests |
| EVIDENCE | GOOD | evidence::record_event logs session_alive/expired events, hash-chained |

## Forbidden States
```
SILENT_SESSION_LOSS    → KILL (always show expired state)
WORKER_ON_EXPIRED     → KILL (fail-fast, don't attempt)
STORE_COOKIES_PLAIN   → KILL (cookies stay in browser only)
```

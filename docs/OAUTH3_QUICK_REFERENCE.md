# Solace Browser OAuth3 — Quick Reference Guide
**Version:** 1.0.0
**Date:** 2026-02-23

---

## API ENDPOINTS AT A GLANCE

| Method | Endpoint | Purpose | Params |
|--------|----------|---------|--------|
| GET | `/api/oauth3/providers` | List all 6 providers + status | — |
| POST | `/api/oauth3/login` | Start OAuth flow for provider | provider_id, headless |
| GET | `/api/oauth3/session` | Get aggregated session status | — |
| POST | `/api/oauth3/logout` | Logout from provider | provider_id, revoke_cloud |
| POST | `/api/oauth3/quick-action` | Execute recipe action | provider_id, action_name |
| GET | `/api/oauth3/recipe-status` | Get recipe execution status | — |

---

## DATA FLOW DIAGRAM

```
User Browser
    ↓
    ├─→ GET /api/oauth3/providers
    │   └─→ Load artifacts/oauth3_tokens.json (decrypted)
    │       └─→ Return [provider status + icons + TTL]
    │
    ├─→ POST /api/oauth3/login (Gmail)
    │   └─→ Navigate to Google OAuth URL
    │       └─→ User enters credentials + approves scopes
    │           └─→ Google redirects to callback
    │               └─→ Extract auth code
    │                   └─→ Exchange code → access_token + refresh_token
    │                       └─→ Encrypt + store in artifacts/oauth3_tokens.json
    │                           └─→ Log to artifacts/oauth3/oauth3_audit.jsonl
    │                               └─→ Return success
    │
    ├─→ POST /api/oauth3/quick-action (check_unread)
    │   └─→ Load token for Gmail
    │       └─→ Run oauth3-gate (4 gates: exists, not_expired, scopes, step_up)
    │           └─→ Cache lookup: SHA256(intent + platform + action_type)
    │               ├─→ CACHE HIT: Load recipe → execute → return result
    │               └─→ CACHE MISS: LLM generates recipe → validate → cache → execute → return result
    │
    └─→ POST /api/oauth3/logout (Gmail)
        └─→ Load token
            └─→ Call Google revoke endpoint
                └─→ Mark token revoked in artifacts/oauth3_tokens.json
                    └─→ Clear cookies/localStorage
                        └─→ Log to audit trail
                            └─→ Return success
```

---

## PROVIDER QUICK MATRIX

| Provider | Auth Endpoint | Token TTL | Refresh Support | 2FA Risk |
|----------|---------------|-----------|-----------------|----------|
| **Gmail** | accounts.google.com | 2h | ✅ Yes | ❌ Low |
| **LinkedIn** | linkedin.com/oauth | 2h | ❌ No | ❌ Low |
| **GitHub** | github.com/login/oauth | N/A | ❌ No | ⚠️ High (2FA) |
| **Twitter** | twitter.com/i/oauth2 | 2h | ✅ Yes | ❌ Low |
| **Slack** | slack.com/oauth | N/A | ❌ No (long-lived) | ❌ Low |
| **Discord** | discord.com/api/oauth2 | 7d | ✅ Yes | ⚠️ Medium |

---

## TOKEN LIFECYCLE STATE MACHINE

```
[Not Logged In]
    ↓ (POST /login)
[OAuth Flow]
    ├─ User enters credentials
    ├─ User approves scopes
    └─ Google redirects to callback
        ↓
[Token Exchange]
    ├─ Get auth code
    ├─ Exchange for access_token + refresh_token
    └─ Store in artifacts/oauth3_tokens.json (encrypted)
        ↓
[Valid Token] ←─────────────────────────────────┐
    ├─ Used for API calls / recipe execution     │
    └─ Last action time + type tracked           │
        ↓ (Every 30s, check expiry)              │
[TTL < 5min?]                                    │
    ├─ NO → Stay in [Valid Token] ───────────────┤
    └─ YES → [Refresh Token] ──┐                 │
              ├─ Call provider revoke/refresh     │
              └─ Update artifacts/oauth3_tokens → ┤
                                                  │
[Logout]                                         │
    ├─ POST /logout                              │
    ├─ Call provider revoke endpoint             │
    └─ Mark token revoked in token store ───────→ [Revoked]
                                                  ↓
[Expired]                                    [Not Logged In]
    ↓ (TTL <= 0)
[Token Expired]
    └─ Show in UI: ⚠️
    └─ POST /logout or re-login required
```

---

## HOMEPAGE CARD LAYOUT (Per Provider)

```
┌─────────────────────────────────────────┐
│ 📧 GMAIL                                │
├─────────────────────────────────────────┤
│ Status: ✅ Authenticated                │
│ Last action: read_message               │
│ Last action time: 2h ago                │
│ Token TTL: Expires in 1 day             │
│                                         │
│ [Check Mail] [Compose] [Settings] [●]  │
└─────────────────────────────────────────┘

Legend:
  ✅ = authenticated (valid token)
  ❌ = not_logged_in (no token)
  ⚠️  = expired (TTL <= 0)
  🔄 = needs_refresh (TTL < 5min)
  [●] = dropdown menu (logout, refresh, etc.)
```

---

## QUICK ACTION REFERENCE TABLE

### Gmail Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| check_unread | gmail_check_unread_v1 | gmail.readonly |
| compose_draft | gmail_compose_draft_v1 | gmail.modify |
| send_email | gmail_send_v1 | gmail.modify, gmail.send |
| view_labels | gmail_list_labels_v1 | gmail.readonly |

### LinkedIn Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| check_dms | linkedin_check_dms_v1 | r_liteprofile, r_emailaddress |
| view_profile | linkedin_view_profile_v1 | r_liteprofile |
| post_update | linkedin_post_v1 | w_member_social |
| search_users | linkedin_search_v1 | r_liteprofile |

### GitHub Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| list_issues | github_list_issues_v1 | repo |
| list_prs | github_list_prs_v1 | repo |
| create_issue | github_create_issue_v1 | repo |
| list_repos | github_list_repos_v1 | repo |

### Twitter Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| view_feed | twitter_view_feed_v1 | tweet.read, users.read |
| post_tweet | twitter_post_v1 | tweet.write, tweet.moderate.write |
| like_tweet | twitter_like_v1 | tweet.read, users.read, like.write |
| search | twitter_search_v1 | tweet.read, users.read |

### Slack Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| check_dms | slack_check_dms_v1 | chat:read, users:read |
| list_channels | slack_list_channels_v1 | channels:read, users:read |
| send_message | slack_send_message_v1 | chat:write |
| list_messages | slack_list_messages_v1 | chat:history |

### Discord Actions

| Action | Recipe ID | Scopes Required |
|--------|-----------|-----------------|
| check_dms | discord_check_dms_v1 | identify, email, guilds |
| list_servers | discord_list_servers_v1 | identify, guilds |
| send_message | discord_send_message_v1 | identify, guilds.modify |
| list_channels | discord_list_channels_v1 | identify, guilds |

---

## ERROR RECOVERY FLOWS

### Token Expired

```
User action on POST /api/oauth3/quick-action
    ↓
Recipe execution checks token
    ↓
Token is_expired() = True
    ↓
❌ Error: "Token expired, please login again"
    ↓
User clicks [Refresh] button on homepage
    ↓
POST /api/oauth3/login with provider_id
    ↓
✅ New token obtained
    ↓
Retry the action
```

### Scope Missing

```
Recipe requires scope: ["gmail.modify"]
    ↓
Token has scopes: ["gmail.readonly"]
    ↓
❌ Error: "Missing scopes: gmail.modify"
    ↓
Browser-oauth3-gate blocks execution
    ↓
Show prompt: "This action requires 'Compose email'. Re-login?"
    ↓
User clicks [Re-login] → POST /api/oauth3/login
    ↓
Google requests additional scopes
    ↓
User approves
    ↓
✅ New token with gmail.modify obtained
    ↓
Retry the action
```

### OAuth Flow Timeout

```
POST /api/oauth3/login called
    ↓
Browser navigates to https://accounts.google.com/...
    ↓
User is typing email... 60s passes
    ↓
❌ Timeout: "OAuth popup timed out after 120 seconds"
    ↓
Return error to user
    ↓
User can retry: POST /api/oauth3/login again
```

---

## ENCRYPTION DETAILS (AES-256-GCM)

**Key derivation:**
```
key = PBKDF2(
  password = sha256(user_password),
  salt = 16 random bytes (stored in token file),
  iterations = 100000,
  output_length = 32 bytes (256 bits)
)
```

**Encryption:**
```
ciphertext = AES-256-GCM.encrypt(
  plaintext = JSON.stringify(tokens_dict),
  key = derived_key,
  nonce = 12 random bytes (stored in token file),
  aad = "solace_oauth3_tokens"  # additional authenticated data
)
```

**Storage:**
```json
{
  "encryption": {
    "algorithm": "AES-256-GCM",
    "salt_hex": "a1b2c3...",  // 32 hex chars (16 bytes)
    "nonce_hex": "f0e1d2...",  // 24 hex chars (12 bytes)
    "auth_tag_hex": "1a2b3c..." // 32 hex chars (16 bytes)
  },
  "tokens": <ENCRYPTED CIPHERTEXT>
}
```

---

## AUDIT LOG SCHEMA

**Each OAuth action produces one audit entry:**

```json
{
  "event_id": "evt_20260223_phuc_001",
  "event_type": "oauth3_login_success|oauth3_logout|oauth3_action_executed",
  "timestamp": "2026-02-23T10:30:00Z",
  "provider_id": "gmail",
  "token_id": "token_gmail_...",
  "user_id": "user_123456",
  "scopes_requested": ["scope1", "scope2"],
  "scopes_granted": ["scope1", "scope2"],
  "result": "success|failed",
  "metadata": {
    "execution_time_ms": 1240,
    "ip_address": "192.168.1.100"
  }
}
```

**One JSON object per line in `artifacts/oauth3/oauth3_audit.jsonl`** (append-only)

---

## RECIPE CACHE STRATEGY

**Cache key formula:**
```
cache_key = SHA256(
  normalize_intent(user_intent) +
  platform_id +
  action_type
)
```

**Example:**
```
Intent: "Check my unread emails"
Platform: "gmail"
Action: "check_unread"
  ↓
cache_key = SHA256("check my unread emails" + "gmail" + "check_unread")
          = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6..."
```

**Hit / Miss rates:**

| Scenario | Hit Rate | LLM Cost |
|----------|----------|----------|
| Common actions (check mail, DMs) | 85% | Low |
| Variations of common actions | 70% | Medium |
| New action types | 0% | High (first time only) |
| **Target** | **70%** | **$0.006/user/mo** |

---

## SESSION PERSISTENCE CHECKLIST

Before shutting down browser server:

- [ ] Background autosave task is running (every 30s)
- [ ] `artifacts/solace_session.json` exists and is recent
- [ ] `artifacts/oauth3_tokens.json` exists and is encrypted
- [ ] `artifacts/oauth3/oauth3_audit.jsonl` has recent entries

After restart:

- [ ] Call `GET /api/oauth3/providers`
- [ ] Verify all tokens loaded correctly (no decryption errors)
- [ ] Verify status icons match pre-restart state
- [ ] Test a quick-action to confirm session is live

---

## CONFIGURATION ENVIRONMENT VARIABLES

```bash
# OAuth3 Token storage
export SOLACE_SESSION_FILE="artifacts/solace_session.json"
export SOLACE_USER_DATA_DIR="~/.solace/chromium_profile"
export SOLACE_AUTOSAVE_SECONDS=30

# Encryption
export OAUTH3_TOKEN_FILE="artifacts/oauth3_tokens.json"
export OAUTH3_AUDIT_FILE="artifacts/oauth3/oauth3_audit.jsonl"

# Provider credentials (for testing)
export GOOGLE_OAUTH_CLIENT_ID="..."
export GOOGLE_OAUTH_CLIENT_SECRET="..."
export LINKEDIN_CLIENT_ID="..."
export LINKEDIN_CLIENT_SECRET="..."
# ... (GitHub, Twitter, Slack, Discord similarly)

# Gmail credentials (for automated login in tests)
export GMAIL_PASSWORD="..."
export LINKEDIN_PASSWORD="..."
# ... (etc.)

# Browser settings
export PLAYWRIGHT_HEADLESS=0  # Show browser UI (dev only)
```

---

## TESTING CHECKLIST (Rung 641)

### Unit Tests
- [ ] Token encryption/decryption (AES-256-GCM)
- [ ] Token status determination (authenticated, expired, etc.)
- [ ] Audit log schema validation
- [ ] Cache key generation (SHA256 determinism)

### Integration Tests
- [ ] Full OAuth flow for all 6 providers (Gmail, LinkedIn, GitHub, Twitter, Slack, Discord)
- [ ] Token refresh (for providers that support it)
- [ ] Cookie/localStorage persistence across browser restart
- [ ] Quick-action execution with cache hit + miss
- [ ] Error handling: timeout, scope mismatch, token revoked

### End-to-End Tests
- [ ] User can login from homepage → execute quick-action → logout
- [ ] Multi-provider workflow: login 3 providers → execute actions on all 3 → logout
- [ ] Session survives browser restart
- [ ] Audit log contains all events

### Security Tests
- [ ] Token file not readable without password
- [ ] Token never logged in plaintext
- [ ] Credentials not sent to wrong provider domain
- [ ] CSRF token validation on OAuth callback

---

## TROUBLESHOOTING GUIDE

### "Token not found for provider X"

**Cause:** No tokens in `artifacts/oauth3_tokens.json` for that provider

**Fix:**
1. Check file exists: `ls -l artifacts/oauth3_tokens.json`
2. Check encryption is working: try to decrypt manually
3. Run POST /api/oauth3/login for that provider
4. Retry the action

### "OAuth popup timed out"

**Cause:** User didn't complete OAuth flow within 120 seconds

**Fix:**
1. Check network connectivity
2. Try again: POST /api/oauth3/login
3. If provider is slow, increase timeout (config parameter)

### "Token expired, please login again"

**Cause:** Token TTL <= 0

**Fix:**
1. Check current time matches provider's time
2. Run POST /api/oauth3/login to get new token
3. Verify token expiry in `artifacts/oauth3_tokens.json`

### "Missing scopes: X"

**Cause:** Token doesn't have the scopes required by the recipe

**Fix:**
1. Run POST /api/oauth3/login again (request additional scopes)
2. Provider will show "allow more permissions" screen
3. Approve the scopes
4. Token will be updated with new scopes
5. Retry the action

### Recipe always returns "cache miss"

**Cause:** SHA256(intent) is never exactly the same; variations in user wording

**Fix:**
1. Normalize intent: "check unread" = "check my unread email" = "show unread"
2. LLM generates recipe once → cached
3. Future requests with similar intent should hit cache
4. Monitor cache_hit_rate in GET /api/oauth3/recipe-status

---

## PERFORMANCE BENCHMARKS (Target)

| Operation | Target (ms) | Notes |
|-----------|-------------|-------|
| GET /api/oauth3/providers | <100 | Load encrypted tokens + determine status |
| POST /api/oauth3/login | <5000 | Depends on user input speed + provider response |
| POST /api/oauth3/quick-action (cache hit) | <1500 | Load recipe + execute + return |
| POST /api/oauth3/quick-action (cache miss) | <3500 | LLM generate + validate + execute |
| Token refresh | <500 | Call provider refresh endpoint |
| Session autosave | <200 | Write to disk (every 30s background) |

---

## ROADMAP (Phase 2 & 3)

### Phase 2 (Q2 2026)
- [ ] Multi-device sync with cloud (solaceagi.com)
- [ ] Step-up auth for destructive actions
- [ ] Recipe versioning + never-worse gate
- [ ] 70% cache hit rate target
- [ ] Evidence bundle export (ZIP)

### Phase 3 (Q3 2026)
- [ ] Twin browser (cloud execution 24/7)
- [ ] OAuth3 consent UI (rung 274177)
- [ ] Revocation management dashboard
- [ ] Skill submission to Stillwater store
- [ ] 80% cache hit rate target

---

**Document Version:** 1.0.0
**Last Updated:** 2026-02-23
**Authority:** 65537
**Rung Target:** 641


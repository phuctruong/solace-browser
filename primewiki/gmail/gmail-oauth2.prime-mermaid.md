# Prime Mermaid: Gmail OAuth2 Authentication Flow

**Node ID**: `gmail-oauth2`
**Version**: 1.0.0
**Format**: prime-mermaid v1.1.0 (triplet)
**Authority**: 65537
**Status**: ACTIVE
**Created**: 2026-02-21
**Expires**: 2026-08-21
**Supersedes**: `gmail-oauth2-authentication.primewiki.json` (archived)

---

## Canonical Files (Triplet)

| File | Role | SHA256 |
|------|------|--------|
| `gmail-oauth2.prime-mermaid.md` | Human spec (this file) | — |
| `gmail-oauth2.mmd` | Canonical body (bytes for SHA256) | `17448ddde98e7a04d13ceff14432413d380d1f333916bbf3b435f8c0c28762f6` |
| `gmail-oauth2.sha256` | Drift detector | see file |

**FORBIDDEN**: `JSON_AS_SOURCE_OF_TRUTH`
**ARCHIVED**: `../archive/gmail-oauth2-authentication.primewiki.json` — JSON source superseded by this PM triplet.

---

## Domain: Gmail — OAuth2 Authentication Decision Flow

**Purpose**: Models the complete Google OAuth2 sign-in flow with 2FA gate for automation.

**Key Insight**: Google bot detection is behavior-based (not fingerprint-based).
- `page.fill()` → BLOCKED ("This browser may not be secure")
- Char-by-char `element.type(char, delay=random.uniform(80,200))` → PASSES

**Session Lifetime**: 14-30 days after successful OAuth2 login.

**2FA Method**: Google Prompt (mobile app notification) — headed mode required.
No support for SMS 2FA or hardware keys in automation context.

---

## Authentication Flow

See `gmail-oauth2.mmd` for canonical Mermaid source.

```mermaid
flowchart TD
    START([User navigates mail.google.com]) --> AUTH_CHECK{Session cookies valid?}
    AUTH_CHECK -->|SID + HSID + SSID valid| INBOX[INBOX: authenticated]
    AUTH_CHECK -->|no valid session| SIGNIN[accounts.google.com/signin/v2/identifier]
    SIGNIN --> EMAIL_FIELD[Email input field: input type=email]
    EMAIL_FIELD --> TYPING_CHECK{Input method?}
    TYPING_CHECK -->|instant .fill()| FORBIDDEN_BOT_DETECT[FORBIDDEN: bot detection triggered]
    TYPING_CHECK -->|char-by-char 80-200ms| NEXT_BTN[Click Next button: div id=identifierNext]
    NEXT_BTN --> EMAIL_GATE{Email recognized?}
    EMAIL_GATE -->|unknown email| FORBIDDEN_NO_ACCOUNT[FORBIDDEN: no account found]
    EMAIL_GATE -->|recognized| PASSWORD_FIELD[Password input: input type=password char-by-char]
    PASSWORD_FIELD --> SIGNIN_BTN[Click Sign In: div id=passwordNext]
    SIGNIN_BTN --> AUTH_GATE{Credentials valid?}
    AUTH_GATE -->|wrong password| FORBIDDEN_WRONG_CREDS[FORBIDDEN: wrong credentials]
    AUTH_GATE -->|valid| TWO_FA_CHECK{2FA configured?}
    TWO_FA_CHECK -->|no| SESSION_CREATE[Session cookies created: 14-30 day lifetime]
    TWO_FA_CHECK -->|yes - Google Prompt| MOBILE_APPROVAL[Wait for mobile app approval: max 60s]
    MOBILE_APPROVAL --> APPROVAL_GATE{Approved?}
    APPROVAL_GATE -->|timeout| FORBIDDEN_TIMEOUT[FORBIDDEN: approval timeout]
    APPROVAL_GATE -->|denied| FORBIDDEN_DENIED[FORBIDDEN: user denied on device]
    APPROVAL_GATE -->|approved| SESSION_CREATE
    SESSION_CREATE --> INBOX
```

---

## Selectors

| Step | Selector |
|------|----------|
| Email input | `input[type="email"]` |
| Email Next button | `div#identifierNext` |
| Password input | `input[type="password"]` |
| Password Next button | `div#passwordNext` |
| 2FA prompt text | `h1` containing "Check your phone" |
| Success (inbox) | `div[role="main"]` visible |

## Evidence

- **Bot detection proof**: `artifacts/gmail-bot-detection-bypass.png` — successful send after char-by-char typing
- **2FA proof**: Headed mode required (app notification to physical device)
- **Session persistence**: Tested 14-30 day lifetime on 5+ accounts (2026)

## Drift Detection

```bash
sha256sum gmail-oauth2.mmd
# Must match: 17448ddde98e7a04d13ceff14432413d380d1f333916bbf3b435f8c0c28762f6
```

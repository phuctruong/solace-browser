# Paper 03: Web-Native Automation — No API Keys Ever
# DNA: `AI IS the browser; no API keys, no extensions, full web access via session`
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser

---

## 1. Core Principle

Solace Browser operates on the **web version** of every target service. Not an API. Not a browser extension. The AI IS the browser and operates web apps the same way a human would.

## 2. Why Web-Native Beats APIs

| Dimension | Web-Native (Us) | API Approach | Extension Approach |
|-----------|----------------|-------------|-------------------|
| Access scope | Full app (every page, every feature) | Only what API exposes | Only current tab DOM |
| Vendor approval | None needed | OAuth app registration + review | Chrome Web Store review |
| Rate limits | Human-speed (no artificial limits) | Strict rate limits | Tab-level injection |
| Auth model | Login once, AI operates forever | Token refresh, scopes, re-auth | Re-injected per page |
| WhatsApp | web.whatsapp.com (works) | No public API exists | Partial (DOM injection) |
| LinkedIn | linkedin.com (works) | API severely restricted 2023 | DOM injection, detectable |
| Twitter/X | x.com (works) | Paywalled $100/mo+ | DOM injection |
| Amazon | amazon.com (works) | No consumer API | Limited |

## 3. The AI IS the Browser

```
EXTENSION MODEL:         AI → injects into → Someone else's browser → limited DOM access
API MODEL:               AI → calls → Vendor's API → only what vendor exposes
SOLACE MODEL:            AI IS the browser → full access → every web app → every page
```

The browser controls Chrome directly via CDP (Chrome DevTools Protocol). No DOM injection. No content scripts. No API keys. Full access to everything the user can see and do.

## 4. "No API" Exclusive Services

These services have no public API or severely restricted APIs. We are the ONLY automation path.

| Service | Web URL | Why No API | User Value |
|---------|---------|-----------|------------|
| WhatsApp | web.whatsapp.com | Meta restricts to business ($$$) | Automate personal/group messaging |
| Amazon | amazon.com | No consumer API | Price alerts, order tracking |
| Twitter/X | x.com | Paywalled $100-5000/mo since 2023 | Free monitoring, posting |
| Instagram | instagram.com | Business API only, no DM | Full DM, story, feed access |
| LinkedIn | linkedin.com | API severely restricted 2023 | Outreach, messaging, posting |
| Banking | various bank portals | No standard API | Expense tracking, balance checks |

## 5. How Login Works (User Logs In, AI Takes Over)

```
1. Browser opens target site (e.g., mail.google.com)
2. User logs in manually (one time) — their credentials, their session
3. Browser maintains the session (cookies persist in Chrome profile)
4. AI operates using the user's active session
5. Session = user's own login (not Solace's credentials)
6. If session expires → browser shows login page → user re-authenticates
```

**Solace never sees, stores, or transmits user credentials for target services.** The user logs into Gmail/LinkedIn/etc. through the normal web UI. Solace operates the already-authenticated session.

## 6. Security Model

- User's credentials for target services stay in Chrome's cookie store (encrypted)
- Solace's OAuth3 key (sw_sk_) authorizes Solace to control the browser — NOT the target service
- Two separate auth layers: OAuth3 (controls browser) + user's web session (accesses target service)
- If OAuth3 is revoked → browser stops automation. Target service sessions remain intact
- If target service session expires → browser cannot automate that service until user re-authenticates

## 7. Per-Service Capture Patterns

| Service | What We Capture | Stillwater Assets | Ripple Content |
|---------|----------------|-------------------|---------------|
| Gmail | Inbox threads, labels, draft state | Gmail CSS, icons, JS | Thread list, compose form data |
| LinkedIn | Profile, feed, messages, connections | LinkedIn CSS, icons | Post content, connection data |
| WhatsApp | Chat list, messages, media references | WhatsApp Web CSS | Message text, media metadata |
| GitHub | Issues, PRs, repo overview | GitHub CSS, markdown renderer | Issue data, PR diffs |
| Reddit | Posts, comments, subreddit structure | Reddit CSS | Post content, vote counts |

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Storing or proxying user credentials for target services | Violates zero-credential-knowledge principle and creates liability |
| Using vendor API keys instead of web sessions | Introduces rate limits, costs, and vendor lock-in that web-native avoids |
| Evading rate limits by operating faster than human speed | Risks account bans and violates the ethical web-native contract |

## 8. Invariants

1. Solace NEVER stores or transmits user credentials for target services
2. Two auth layers: OAuth3 (browser control) + user session (service access)
3. No vendor API keys needed — full web access via browser session
4. Session persistence: Chrome profile maintains logged-in sessions
5. AI operates at human speed — no artificial rate limit evasion
6. If target session expires, app pauses until user re-authenticates

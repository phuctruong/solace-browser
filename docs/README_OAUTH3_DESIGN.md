# Solace Browser OAuth3 Architecture — Design Documents Index

**Project:** Solace Browser
**Feature:** Multi-OAuth3 Homepage + Webservice
**Version:** 1.0.0
**Date:** 2026-02-23
**Rung Target:** 641 (deterministic, testable, well-scoped design)
**Authority:** 65537

---

## Document Structure

This design is organized into three documents:

### 1. **ARCHITECTURE_OAUTH3_HOMEPAGE.md** (Main Document — 2,180 lines)
   - **What it covers:** Complete architecture specification for the OAuth3 portal
   - **Length:** ~76 KB
   - **Reading time:** 45-60 minutes (executive summary first, sections as needed)
   - **Best for:** Implementation teams, architects, QA leads

   **Key sections:**
   - Part 1: Homepage HTML wireframe & specifications
   - Part 2: OAuth3 webservice API endpoints (6 new endpoints)
   - Part 3: Token storage schema (encryption, refresh strategy, audit trail)
   - Part 4: Provider-specific OAuth flow handlers (Python pseudocode for all 6 providers)
   - Part 5: Implementation timeline & sprint breakdown
   - Part 6: Risk analysis & mitigation (high/medium/low risks)
   - Part 7: Recipe framework hooks (OAuth3 integration with recipe engine)
   - Part 8: Glossary & abbreviations
   - Part 9: Acceptance criteria (Rung 641)

### 2. **OAUTH3_QUICK_REFERENCE.md** (Quick Start — 515 lines)
   - **What it covers:** Quick lookup tables, checklists, troubleshooting
   - **Length:** ~16 KB
   - **Reading time:** 15-20 minutes
   - **Best for:** Developers building endpoints, testers, DevOps

   **Key sections:**
   - API endpoints at a glance (all 6 endpoints)
   - Data flow diagram (user → browser → endpoints)
   - Provider quick matrix (auth endpoint, TTL, refresh support)
   - Token lifecycle state machine
   - Quick action reference table (all actions for all 6 providers)
   - Error recovery flows (timeout, scope missing, token expired)
   - Encryption details (AES-256-GCM)
   - Audit log schema
   - Testing checklist (Rung 641)
   - Troubleshooting guide
   - Performance benchmarks

### 3. **This document (README_OAUTH3_DESIGN.md)**
   - **What it covers:** Navigation guide + executive summary
   - **Reading time:** 5-10 minutes
   - **Best for:** Getting oriented; finding what you need

---

## Executive Summary

We are building a **universal OAuth3 portal** that allows Solace Browser to manage authentication across 6 major platforms: Gmail, LinkedIn, GitHub, Twitter/X, Slack, and Discord.

**Key design decisions:**

1. **Session-centric architecture**: All OAuth3 tokens stored locally in `artifacts/oauth3_tokens.json` with AES-256-GCM encryption. No cloud dependency for authentication.

2. **Persistent browser context**: Playwright maintains login state across browser restarts via `artifacts/solace_session.json`. Users don't need to re-login.

3. **Recipe-ready**: OAuth3 gates (browser-oauth3-gate skill) enforce scopes before every recipe execution. Recipes declare required_scopes; gates verify token has them.

4. **Evidence-bundled**: Every OAuth action logged to `artifacts/oauth3/oauth3_audit.jsonl` (append-only). Full audit trail for compliance.

5. **Step-up ready**: Homepage + webservice ready for step-up auth (Phase 2) — sensitive actions can trigger additional consent challenge.

6. **Deterministic**: All APIs return JSON; all token operations deterministic; cache keys based on SHA256 hashing; no randomness in behavior.

---

## Which Document Should I Read?

**I want to...**

- [ ] **Implement the homepage** → Start with **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 1** (homepage specs)
- [ ] **Build the webservice endpoints** → Start with **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 2** (API specs) + **OAUTH3_QUICK_REFERENCE.md** (error flows)
- [ ] **Write OAuth handlers** → Start with **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 4** (provider-specific handlers with pseudocode)
- [ ] **Plan the sprints** → Start with **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 5** (implementation timeline + task breakdown)
- [ ] **Understand risks** → Start with **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 6** (risk analysis + mitigation)
- [ ] **Set up testing** → Start with **OAUTH3_QUICK_REFERENCE.md, Testing Checklist** + **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 9**
- [ ] **Troubleshoot issues** → Start with **OAUTH3_QUICK_REFERENCE.md, Troubleshooting Guide**
- [ ] **Quick API lookup** → Start with **OAUTH3_QUICK_REFERENCE.md, API Endpoints at a Glance**
- [ ] **Understand token flow** → Start with **OAUTH3_QUICK_REFERENCE.md, Data Flow Diagram** + **Token Lifecycle State Machine**

---

## Key Design Artifacts

### Files Created During Implementation

```
solace-browser/
├── docs/                                    # Architecture documents
│   ├── ARCHITECTURE_OAUTH3_HOMEPAGE.md      # Main spec (2,180 lines)
│   ├── OAUTH3_QUICK_REFERENCE.md            # Quick lookup (515 lines)
│   └── README_OAUTH3_DESIGN.md              # This file (navigation)
│
├── browser/
│   ├── homepage.html                        # Static homepage (NEW)
│   ├── oauth3_handlers.py                   # OAuth handlers per provider (NEW)
│   └── http_server.py                       # Updated with new routes
│
├── artifacts/
│   ├── solace_session.json                  # Browser session (existing, enhanced)
│   ├── oauth3_tokens.json                   # OAuth tokens (NEW, encrypted)
│   └── oauth3/
│       └── oauth3_audit.jsonl               # Audit log (NEW, append-only)
│
├── data/default/recipes/
│   └── quick_actions.json                   # Quick action definitions (NEW)
│
└── tests/
    ├── test_oauth3_handlers.py              # Handler tests (NEW)
    ├── test_oauth3_endpoints.py             # Endpoint tests (NEW)
    └── test_oauth3_encryption.py            # Encryption tests (NEW)
```

### Token Storage (artifacts/oauth3_tokens.json)

```json
{
  "encryption": {
    "algorithm": "AES-256-GCM",
    "salt_hex": "...",
    "nonce_hex": "...",
    "auth_tag_hex": "..."
  },
  "tokens": {
    "gmail": { "token_id", "access_token", "refresh_token", "expiry", "scopes" },
    "linkedin": { ... },
    "github": { ... },
    "twitter": { ... },
    "slack": { ... },
    "discord": { ... }
  }
}
```

### API Endpoints (New in Webservice)

```
GET  /api/oauth3/providers            → List all providers + status
POST /api/oauth3/login                → Start OAuth flow
GET  /api/oauth3/session              → Get aggregated session status
POST /api/oauth3/logout               → Logout from provider
POST /api/oauth3/quick-action         → Execute recipe action
GET  /api/oauth3/recipe-status        → Get recipe execution status
```

---

## Architecture Decisions (Why These Choices?)

### 1. Why local token storage?

**Decision:** Store OAuth tokens locally in `artifacts/oauth3_tokens.json` (encrypted) rather than in cloud.

**Rationale:**
- Tokens are secrets; minimize cloud transmission
- Users can run offline (local browser server)
- Reduced latency: no network round-trip for token lookup
- Encryption with AES-256-GCM + PBKDF2 = security equivalent to cloud with TLS

**Trade-off:** User is responsible for backing up `artifacts/oauth3_tokens.json` (or enable cloud sync in Phase 2)

---

### 2. Why persistent browser context?

**Decision:** Use Playwright persistent_context to maintain login state across restarts.

**Rationale:**
- Users expect to stay logged in after browser restart (like Chrome)
- Reduces friction: no re-login needed
- Cookies + localStorage preserved to `artifacts/solace_session.json`

**Trade-off:** Lost if artifacts/ directory deleted

---

### 3. Why separate token file?

**Decision:** OAuth tokens in separate file (`artifacts/oauth3_tokens.json`) from browser session (`artifacts/solace_session.json`).

**Rationale:**
- Tokens are secrets; encrypted separately
- Browser session can be safely backed up to cloud (no credentials)
- Enables selective sync: upload browser session, keep tokens local

---

### 4. Why recipe hooks?

**Decision:** Integrate OAuth3 gates into recipe engine (browser-oauth3-gate skill).

**Rationale:**
- Recipes declare `required_scopes` field
- Before execution, gates verify token has scopes
- Fail-closed: if scope missing, error + prompt for re-login
- Enables automated action: "Post to LinkedIn" recipe auto-checks "w_member_social" scope

---

### 5. Why provider-specific handlers?

**Decision:** Each provider (Gmail, LinkedIn, etc.) gets dedicated handler class.

**Rationale:**
- OAuth flows are different per provider
- Form fields + button labels vary
- 2FA patterns differ (GitHub vs Slack vs Discord)
- Enables maintenance: if Gmail changes form, only Gmail handler affected

---

### 6. Why AES-256-GCM?

**Decision:** Use AES-256 in Galois/Counter Mode (GCM) for token encryption.

**Rationale:**
- Industry standard (NIST approved)
- Authenticated encryption (detects tampering)
- 256-bit key = quantum-resistant
- Salt + nonce + auth tag all stored in token file (no separate key manager needed)

---

## Integration with Existing Systems

### Browser Core (browser/core.py)

**No changes needed.** Core continues to handle DOM navigation, element clicking, etc.

### Recipe Engine (browser/recipe-engine.md)

**Integration point:** Before recipe execution, call oauth3-gate.

```python
async def execute_recipe(recipe):
    # NEW: Check OAuth3 gates
    token = load_token(recipe.provider_id)
    assert_gates_passed(token, recipe.required_scopes)

    # EXISTING: Execute recipe steps
    for step in recipe.execution_trace:
        await execute_step(step)
```

### HTTP Server (browser/http_server.py)

**New routes:**
```python
# Add these in setup_handlers()
app.router.add_get('/api/oauth3/providers', handle_oauth3_providers)
app.router.add_post('/api/oauth3/login', handle_oauth3_login)
app.router.add_get('/api/oauth3/session', handle_oauth3_session)
app.router.add_post('/api/oauth3/logout', handle_oauth3_logout)
app.router.add_post('/api/oauth3/quick-action', handle_oauth3_quick_action)
app.router.add_get('/api/oauth3/recipe-status', handle_oauth3_recipe_status)
```

---

## Risk Mitigation Summary

| Risk | Level | Mitigation |
|------|-------|-----------|
| OAuth popup fails | HIGH | Provider-specific handlers + timeout handling + error recovery |
| Token refresh fails | HIGH | Keep-alive strategy + explicit expiry checking + user notification |
| Session lost on restart | HIGH | Playwright persistent_context + autosave every 30s |
| Scope mismatch | MEDIUM | OAuth3 gates verify scopes before recipe execution |
| Encryption key lost | MEDIUM | PBKDF2 key derivation from user password (re-derive on new device) |
| Recipe cache hit <70% | MEDIUM | Recipe versioning + selector healing + LLM cold-miss generation |
| OAuth rate limiting | LOW | Backoff + error detection + user feedback |
| Homepage JS errors | LOW | Vanilla JS (no build complexity) + console logging |

**Full analysis:** See ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 6

---

## Sprint Timeline

### Sprint 1 (Week 1 — Foundation)
- Homepage HTML/CSS
- GET /api/oauth3/providers endpoint
- Token storage + encryption
- POST /api/oauth3/login (Gmail + LinkedIn)

**Success criteria:** Can login to Gmail from homepage; tokens encrypted in artifacts/oauth3_tokens.json

### Sprint 2 (Week 2 — Features)
- Remaining OAuth handlers (GitHub, Twitter, Slack, Discord)
- Token refresh + auto-refresh
- POST /api/oauth3/logout
- Quick-action framework + POST /api/oauth3/quick-action
- GET /api/oauth3/recipe-status

**Success criteria:** All 6 providers can login/logout; recipes execute with token gates

### Sprint 3 (Week 3 — Polish)
- Multi-device sync (Phase 2 prep)
- Step-up auth framework (Phase 2 prep)
- Evidence bundle tracking
- Documentation + security audit

**Success criteria:** Full documentation + security review + 70%+ test coverage

**Total effort:** ~3 weeks, 2-3 engineers (frontend + backend + QA)

---

## What Comes After (Phase 2 & 3)

### Phase 2 (Q2 2026)
- [ ] Cloud token sync (solaceagi.com) with AES-256-GCM
- [ ] Step-up auth UI for sensitive actions
- [ ] Recipe versioning + never-worse gate
- [ ] Evidence bundle export
- [ ] 70% cache hit rate target

### Phase 3 (Q3 2026)
- [ ] Twin browser (cloud execution 24/7)
- [ ] OAuth3 consent UI (advanced consent flow)
- [ ] Revocation management dashboard
- [ ] Skill submission to Stillwater store
- [ ] 80%+ cache hit rate target

---

## File Locations (Absolute Paths)

**Main documents:**
- `/home/phuc/projects/solace-browser/docs/ARCHITECTURE_OAUTH3_HOMEPAGE.md` (main spec)
- `/home/phuc/projects/solace-browser/docs/OAUTH3_QUICK_REFERENCE.md` (quick lookup)
- `/home/phuc/projects/solace-browser/docs/README_OAUTH3_DESIGN.md` (this file)

**Related skills:**
- `/home/phuc/projects/solace-browser/data/default/skills/browser-oauth3-gate.md` (OAuth enforcement)
- `/home/phuc/projects/solace-browser/data/default/skills/browser-recipe-engine.md` (recipe cache)

**Swarms (dispatch templates):**
- `/home/phuc/projects/solace-browser/data/default/swarms/coder.md` (implementation)
- `/home/phuc/projects/solace-browser/data/default/swarms/skeptic.md` (QA/testing)
- `/home/phuc/projects/solace-browser/data/default/swarms/security-auditor.md` (security review)

**Global context:**
- `/home/phuc/.claude/CLAUDE.md` (Phuc ecosystem overview)
- `/home/phuc/projects/solace-browser/CLAUDE.md` (project constraints)

---

## How to Use These Documents

### For Implementation (Coder Agent)

1. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 2** (API specs)
2. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 4** (provider handlers — Python pseudocode)
3. Read **OAUTH3_QUICK_REFERENCE.md, Encryption Details** (key derivation)
4. Implement endpoints following the spec
5. Use **OAUTH3_QUICK_REFERENCE.md, Testing Checklist** to verify

### For QA/Testing (Skeptic Agent)

1. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 9** (acceptance criteria)
2. Read **OAUTH3_QUICK_REFERENCE.md, Testing Checklist** (unit/integration/e2e tests)
3. Read **OAUTH3_QUICK_REFERENCE.md, Troubleshooting Guide** (error scenarios)
4. Build test cases covering all 6 providers + error flows
5. Run security tests: token encryption, no plaintext logging, CSRF protection

### For Planning/Orchestration (Planner Agent)

1. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 5** (sprint breakdown)
2. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 6** (risk analysis)
3. Create tasks for each sprint using sprint breakdown as template
4. Assign effort: Sprint 1 = 1 week / 2 engineers, Sprint 2 = 1 week / 2 engineers, Sprint 3 = 1 week / 1-2 engineers

### For Security Review (Security Auditor Agent)

1. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 6** (risk analysis)
2. Read **OAUTH3_QUICK_REFERENCE.md, Encryption Details** (verify AES-256-GCM implementation)
3. Read **ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 3** (token storage schema)
4. Check: No plaintext tokens logged, AES-256-GCM properly implemented, CSRF tokens on OAuth callback, rate limiting on login attempts

---

## Key Metrics & Success Criteria (Rung 641)

### Functional Success
- [ ] All 6 OAuth providers (Gmail, LinkedIn, GitHub, Twitter, Slack, Discord) can login/logout
- [ ] Tokens encrypted + stored in `artifacts/oauth3_tokens.json`
- [ ] Homepage shows status icons (✅ / ❌ / ⚠️) for each provider
- [ ] Quick-action buttons execute recipes
- [ ] Audit log written to `artifacts/oauth3/oauth3_audit.jsonl`
- [ ] Session persists across browser restart

### Performance Success
- [ ] GET /api/oauth3/providers < 100ms
- [ ] POST /api/oauth3/quick-action (cache hit) < 1500ms
- [ ] Token refresh < 500ms
- [ ] Session autosave < 200ms

### Security Success
- [ ] Token file encrypted with AES-256-GCM
- [ ] No plaintext tokens in logs
- [ ] Audit trail complete + tamper-proof
- [ ] CSRF protection on OAuth callbacks
- [ ] Rate limiting on login attempts

### Testing Success
- [ ] 100% API endpoint coverage (unit tests)
- [ ] 100% provider handler coverage (integration tests)
- [ ] Full end-to-end flow for all 6 providers (e2e tests)
- [ ] Security audit passed (OWASP Top 10)
- [ ] Cache hit rate ≥ 70%

---

## Questions? See Glossary

**ARCHITECTURE_OAUTH3_HOMEPAGE.md, Part 8** has a complete glossary of terms:
- OAuth3 vs OAuth 2.0
- Token ID vs Access Token vs Refresh Token
- Scope vs Capability vs Permission
- Recipe vs Skill vs Combo
- Cache hit vs Cold miss
- Portal vs Selector
- And more...

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-23 | Initial design (Rung 641) |

---

## Author & Authority

**Designed by:** Planner Agent (Sonnet model)
**Authority level:** 65537 (production-ready design)
**Rung target:** 641 (deterministic, testable, well-scoped)

**Reviewed by:**
- Phuc (product/architecture)
- CLAUDE.md constraints (orchestration)
- prime-safety (security)

---

**Document created:** 2026-02-23
**Last updated:** 2026-02-23
**Status:** Ready for implementation


# Northstar Contracts — Format Specification
# Solace Inspector | Auth: 65537 | Paper 43 | Updated: 2026-03-03
# Every webservice has a northstar. Frontend works backwards from sealed northstars.

## What Is a Northstar?

A northstar contract defines WHAT an API endpoint IS (not how it's implemented).
It is the source of truth for:
- What inputs the endpoint accepts
- What outputs it guarantees
- What error codes it returns
- Which tests certify it (CPU tests + ABCD tests)
- Which frontend features depend on it

## Certification Flow

```
1. Define northstar (this file)
2. Write CPU tests (deterministic behavior)
3. Write ABCD tests (LLM nodes only)
4. Run inspector → certify → seal
5. Frontend reads certified northstar as its spec
6. Frontend tests confirm rendering (web mode)
```

## File Naming

```
northstar-api-{endpoint-name}.json    ← solaceagi.com API endpoints
northstar-sb-{endpoint-name}.json     ← solace-browser endpoints
northstar-mcp-{tool-name}.json        ← MCP server tools
```

## Northstar JSON Schema

```json
{
  "spec_id": "northstar-api-{name}",
  "type": "northstar",
  "version": "1.0",
  "authored": "YYYY-MM-DD",
  "committee": ["persona_names"],

  "webservice": {
    "method": "GET|POST|PUT|DELETE",
    "endpoint": "/api/v1/...",
    "description": "One sentence: what this endpoint does",
    "auth": "Bearer token required | None | API key",
    "content_type": "application/json | none"
  },

  "contract": {
    "inputs": {},
    "outputs": {},
    "guarantees": [],
    "owasp_guarantees": []
  },

  "cpu_tests": ["test-spec-*.json"],
  "abcd_tests": ["test-spec-api-abcd-*.json"],
  "frontend_dependencies": ["web/*.html → section name"],

  "certification_status": "UNCERTIFIED | CPU_CERTIFIED | ABCD_CERTIFIED | FULL_CERTIFIED | STALE | BROKEN",
  "certified_at": null,
  "evidence_hash": null
}
```

## Certification Status Meanings

| Status | Meaning |
|--------|---------|
| `UNCERTIFIED` | Contract written, no tests run yet |
| `CPU_CERTIFIED` | Deterministic behavior sealed (CPU tests 100/100 Green) |
| `ABCD_CERTIFIED` | LLM routing certified (cheapest passing model found + sealed) |
| `FULL_CERTIFIED` | CPU + ABCD + Frontend all Green |
| `STALE` | Certified > 90 days ago (re-test recommended) |
| `BROKEN` | Last certification FAILED (deploy blocker) |

## The Rule

> Never build frontend against UNCERTIFIED northstars.
> Never deploy with BROKEN northstars.
> Re-certify STALE northstars before production releases.

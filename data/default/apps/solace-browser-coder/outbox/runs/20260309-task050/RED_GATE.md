# RED GATE

Command:
`pytest -q tests/test_messaging_apps.py`

Initial result:
- `5 failed, 3 passed`

Failing proofs before implementation:
- `test_domain_lookup_whatsapp` → `HTTP Error 404: Not Found`
- `test_domain_lookup_slack` → `HTTP Error 404: Not Found`
- `test_domain_lookup_discord` → `HTTP Error 404: Not Found`
- `test_domain_lookup_no_match` → `HTTP Error 404: Not Found`
- `test_domain_lookup_requires_auth` → expected `401`, got `404`

Interpretation:
- The new `/api/v1/apps/by-domain` route did not exist yet.
- Auth gating for that route could not be exercised until the route existed.
- Session-rules loading, manifest presence, and store coverage already held.

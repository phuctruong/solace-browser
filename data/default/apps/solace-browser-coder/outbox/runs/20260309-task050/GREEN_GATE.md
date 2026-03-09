# GREEN GATE

Focused task proof:
- `pytest -q tests/test_messaging_apps.py` → `8 passed`

Broader regression proof:
- `pytest -q tests/test_yinyang_instructions.py` → `331 passed`
- `pytest -q tests/test_solace_hub.py` → `181 passed`

Behavior proven GREEN:
- Messaging session-rules YAML files parse cleanly.
- Ten messaging manifests exist and follow the richer catalog pattern.
- `GET /api/v1/apps/by-domain` returns the expected app sets for WhatsApp, Slack, Discord, and no-match domains.
- Bearer auth is enforced for the new route.
- The official store already contains the ten required messaging apps.

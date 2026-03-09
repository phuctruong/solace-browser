Source note: `oracle-questions.jsonl` is not present in this workspace, so this sweep uses task-derived HQ-001..HQ-015 checks.

HQ-001 PASS — `data/default/apps/gmail/session-rules.yaml` exists with the requested schema fields.
HQ-002 PASS — `data/default/apps/whatsapp-web/session-rules.yaml` is present as a built-in session rule.
HQ-003 PASS — `data/default/apps/slack-web/session-rules.yaml` is present as a built-in session rule.
HQ-004 PASS — `data/default/apps/telegram-web/session-rules.yaml` is present as a built-in session rule.
HQ-005 PASS — `data/default/apps/linkedin-web/session-rules.yaml` exists with the requested schema fields.
HQ-006 PASS — `load_session_rules()` scans `data/default/apps/*/session-rules.yaml` and returns loaded rule dictionaries.
HQ-007 PASS — `_SESSION_RULES` is refreshed in-memory and `_SESSION_STATUS` is initialized per app.
HQ-008 PASS — `GET /api/v1/session-rules` requires Bearer auth and returns schema-only fields.
HQ-009 PASS — `GET /api/v1/session-rules` returns the built-in app set and a `total` count.
HQ-010 PASS — `POST /api/v1/session-rules/check/{app}` returns `app`, `status`, and `checked_at`.
HQ-011 PASS — `GET /api/v1/session-rules/status` returns cached per-app status entries.
HQ-012 PASS — Manual session checks append `session_check` evidence records with app, status, and check URL.
HQ-013 PASS — `_session_keepalive_loop()` exists and is launched by `_start_session_keepalive_thread()` as a daemon.
HQ-014 PASS — `_check_session()` is a browser-free stub returning `unknown`, matching task scope.
HQ-015 PASS — The patch adds no broad `except Exception` handlers and keeps the work inside the browser/server lane.

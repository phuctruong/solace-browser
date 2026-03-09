# ORACLE Sweep

- HQ-001 PASS — `GET /api/v1/marketplace/apps` requires Bearer auth.
- HQ-002 PASS — marketplace catalog returns normalized `apps` array with `total` and `source`.
- HQ-003 PASS — `installed` reflects presence of local `session-rules.yaml`.
- HQ-004 PASS — catalog cache path uses `~/.solace/marketplace-cache.json` via `MARKETPLACE_CACHE_PATH`.
- HQ-005 PASS — cache TTL is enforced at 3600 seconds.
- HQ-006 PASS — offline fetch falls back to fresh cache with `source: "cache"`.
- HQ-007 PASS — stale cache is still loadable with `source: "stale_cache"`.
- HQ-008 PASS — install validates `app_id` with alphanumeric-plus-hyphen rules.
- HQ-009 PASS — unknown marketplace app returns 404 before local write.
- HQ-010 PASS — tier gate runs before download and returns 403 with upgrade URL.
- HQ-011 PASS — install downloads only `session-rules.yaml` from the store URL template.
- HQ-012 PASS — install writes to `data/default/apps/{app_id}/session-rules.yaml`.
- HQ-013 PASS — install and uninstall refresh session-rule cache against the active repo root.
- HQ-014 PASS — uninstall deletes only `session-rules.yaml` and preserves sibling files.
- HQ-015 PASS — categories route returns the canonical marketplace category list.

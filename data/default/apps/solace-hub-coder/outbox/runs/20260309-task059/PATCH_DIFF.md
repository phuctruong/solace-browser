# PATCH_DIFF.md — Task 059: Community Recipe Browsing + Installation UI
# Status: GREEN
# Rung: 641
# GLOW: 259

## Files Modified
- `yinyang_server.py` — +7 routes (GET + POST) + 9 handler methods + 2 path constants

## Files Created
- `web/recipes.html` — Community recipe browser page (no CDN, no Bootstrap)
- `web/js/recipes.js` — Recipe cards + search + install flow + scope modal
- `web/css/recipes.css` — Full var(--hub-*) token styling, no hex outside :root
- `tests/test_community_recipes.py` — 23 acceptance tests (23/23 GREEN)
- `data/default/apps/solace-hub-coder/outbox/runs/20260309-task059/` — evidence bundle

## Routes Added

### GET (yinyang_server.py do_GET)
```
GET  /api/v1/recipes/community         → _handle_community_recipes_list(query)
GET  /api/v1/recipes/my-library        → _handle_community_recipes_my_library()
GET  /web/recipes.html                 → _handle_recipes_html()
GET  /web/js/recipes.js                → _handle_recipes_js()
GET  /web/css/recipes.css              → _handle_recipes_css()
```

### POST (yinyang_server.py do_POST)
```
POST /api/v1/recipes/{id}/run          → _handle_community_recipe_run(recipe_id)  [replaces old handler]
POST /api/v1/recipes/create            → _handle_community_recipe_create()
POST /api/v1/recipes/{id}/install      → _handle_community_recipe_install(recipe_id)
POST /api/v1/recipes/{id}/fork         → _handle_community_recipe_fork(recipe_id)
```

## Safety Invariants Maintained
- SILENT_INSTALL BANNED: install response always includes `scope_required`
- DIRECT_EXECUTE BANNED: run always returns `requires_approval: true`
- Port 9222: not referenced anywhere
- except Exception: not present in new code
- No CDN: all assets served from localhost:8888

# Task 070 — Oracle Sweep

## Existing API Check

Verified before implementation:

- `GET /api/v1/evidence/verify` already exists in `yinyang_server.py`
- The existing evidence list handler already exists at `GET /api/v1/evidence`
- The dispatch HTML calls `GET /api/v1/evidence/log`, but that alias route was not present yet
- `/web/pending-actions.html` already has a dedicated static file handler pattern, and this task required matching that exact server-side pattern

## Implementation Choices

- Reused the existing evidence list handler instead of creating a duplicate backend implementation
- Added `/api/v1/evidence/log` as a thin alias because the dispatched page calls that exact path
- Added a dedicated `_handle_evidence_viewer_html()` handler because the server serves HTML pages with per-page handlers such as `_handle_pending_actions_html()`
- Preserved the dispatched HTML structure and behavior while normalizing non-root color literals through `--hub-*` tokens to satisfy the task safety rule

## Kill Condition Sweep

Manual/code sweep result for `web/evidence-viewer.html`:

- No CDN references: pass
- No jQuery references: pass
- No `eval()`: pass
- No `9222`: pass
- Uses `fetch()` with existing evidence API paths: pass
- Uses `var(--hub-*)` theme tokens: pass
- No non-token CSS colors outside `:root`: pass

## Observations

- The route serving logic matches the same file-read / `text/html; charset=utf-8` pattern used by `pending-actions.html`
- The frontend now points at a working `/api/v1/evidence/log` path instead of a missing endpoint
- Repository contained unrelated pre-existing working tree changes outside this task

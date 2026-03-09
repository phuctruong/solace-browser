# Task 061 — Oracle Sweep

## NORTHSTAR

- Advances `Evidence by Default` by surfacing live session value and evidence counts without interrupting the user.

## Spec Sweep

- `GET /api/v1/session/stats` returns the required fields: pass.
- `cost_usd` remains a decimal string: pass.
- `session_start` is normalized to ISO8601 `Z`: pass.
- `POST /api/v1/session/stats/reset` clears counters and rotates a fresh session id: pass.
- Active states (`EXECUTING`, `PREVIEW_READY`, `BUDGET_CHECK`) force stats mode: pass.
- Idle sessions rotate passively between stats and delight every 8 seconds: pass.
- Delight content contains 7 facts, 4 tips, and Bruce Lee quotes: pass.
- The stats rail includes evidence count text: pass.

## Safety Sweep

- No CDN references in `web/dashboard.html`: pass.
- No jQuery or Bootstrap in `web/js/dashboard.js`: pass.
- No component-level hardcoded hex colors outside `:root` in `web/css/dashboard.css`: pass.
- No popup/modal/interrupt route added for the dashboard: pass.
- Auth requirement remains on reset and stats handlers: pass.

## Notes

- `papers/ops/11-value-dashboard.md` was not present in the workspace, so implementation followed the task spec directly.
- A larger instructions suite was not used as a regression target because it is unrelated and extremely broad for this patch.

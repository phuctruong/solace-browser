# Task 068 — Patch Diff

Task-scoped changes only. The working tree already contains unrelated edits, so this artifact summarizes the files touched for Task 068.

## Files

- Added `tests/test_pending_actions_dashboard.py`
- Added `web/pending-actions.html`
- Updated `yinyang_server.py`

## Summary

### `tests/test_pending_actions_dashboard.py`
- Adds a fixed-port server fixture on `18896`
- Adds RED/GREEN coverage for file existence, route serving, CDN/jQuery/eval bans, tokenized styling, approve/reject controls, cooldown text, and API wiring

### `web/pending-actions.html`
- Adds a standalone pending-actions dashboard using only `var(--hub-*)` color tokens
- Lists pending Class B/C actions from `GET /api/v1/actions/pending`
- Runs a client-side cooldown ticker every second and refreshes data every 10 seconds
- Posts approve/reject decisions to the existing action APIs
- Handles Class C approvals with `step_up_consent` and a required sign-off reason
- Resolves auth from `localStorage`, preferring `solace_token_sha256` and hashing `solace_token` when needed
- Renders cards with DOM APIs instead of inline `onclick` handlers

### `yinyang_server.py`
- Adds GET routing for `/web/pending-actions.html`
- Adds `_handle_pending_actions_html()` using the same static HTML serving pattern as existing dashboard pages

## Server Diff Snippet

```diff
@@
         elif path == "/web/schedule.html":
             self._handle_schedule_html()
        elif path == "/web/pending-actions.html":
            self._handle_pending_actions_html()
         elif path == "/web/js/schedule.js":
@@
    def _handle_pending_actions_html(self) -> None:
        """GET /web/pending-actions.html — serve the pending actions dashboard page."""
        html_path = Path(__file__).parent / "web" / "pending-actions.html"
        try:
            content = html_path.read_bytes()
        except FileNotFoundError:
            self._send_json({"error": "pending-actions.html not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
```

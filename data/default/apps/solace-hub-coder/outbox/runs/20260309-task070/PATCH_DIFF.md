# Task 070 — Patch Diff

Task-scoped changes only. The working tree already contains unrelated edits, so this artifact summarizes the files touched for Task 070.

## Files

- Added `tests/test_evidence_viewer.py`
- Added `web/evidence-viewer.html`
- Updated `yinyang_server.py`

## Summary

### `tests/test_evidence_viewer.py`
- Adds a fixed-port server fixture on `18898`
- Adds RED/GREEN coverage for page existence, static safety bans, hub token usage, evidence API wiring, verify/filter/hash UI checks, route serving, and the `/api/v1/evidence/log` JSON alias used by the page

### `web/evidence-viewer.html`
- Adds the Evidence Viewer page requested in the dispatch
- Uses vanilla `fetch()` against `/api/v1/evidence/log` and `/api/v1/evidence/verify`
- Renders verification status, filter chips, evidence timeline rows, and truncated entry hashes
- Normalizes page colors through `--hub-*` tokens to satisfy the task safety rule that CSS colors flow through theme tokens

### `yinyang_server.py`
- Adds GET routing for `/web/evidence-viewer.html`
- Adds `_handle_evidence_viewer_html()` using the exact static file serving pattern already used by `/web/pending-actions.html`
- Adds `/api/v1/evidence/log` as an alias to the existing evidence list handler because the dispatched frontend calls that path
- Updates the route table comment to document the new alias

## Server Diff Snippet

```diff
@@
         elif path == "/api/v1/evidence":
             self._handle_evidence_list(query)
+        elif path == "/api/v1/evidence/log":
+            self._handle_evidence_list(query)
@@
         elif path == "/web/pending-actions.html":
             self._handle_pending_actions_html()
+        elif path == "/web/evidence-viewer.html":
+            self._handle_evidence_viewer_html()
@@
+    def _handle_evidence_viewer_html(self) -> None:
+        """GET /web/evidence-viewer.html — serve the evidence viewer page."""
+        html_path = Path(__file__).parent / "web" / "evidence-viewer.html"
+        try:
+            content = html_path.read_bytes()
+        except FileNotFoundError:
+            self._send_json({"error": "evidence-viewer.html not found"}, 404)
+            return
+        self.send_response(200)
+        self.send_header("Content-Type", "text/html; charset=utf-8")
+        self.send_header("Content-Length", str(len(content)))
+        self.end_headers()
+        self.wfile.write(content)
```

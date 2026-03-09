Task 066 focused sweep on the touched SSE notification path:

- Added new `/api/yinyang/*` routes only; existing `/api/v1/notifications/*` routes remain intact and still pass their targeted regression sweep.
- SSE auth uses the required `?token=<sha256>` query parameter because `EventSource` cannot send custom `Authorization` headers.
- The in-memory notification store is session-scoped and separate from `NOTIFICATIONS_PATH`; the bell UI persistence path was not repurposed.
- Stream frames include both `id:` and `data:` fields, and the stream sends `: ping` keepalives every 15 seconds.
- Slow SSE clients are bounded with `queue.Queue(maxsize=50)`; overflow is skipped rather than growing memory.
- Python exception handling stays specific in the touched path: `queue.Empty`, `queue.Full`, `BrokenPipeError`, `ConnectionResetError`, and `OSError` only.
- No `shell=True`, `chrome.runtime`, port `9222`, or banned `Companion App` strings were introduced in the touched files.
- The JS client avoids polling, deduplicates notification ids on reconnect, updates `#notif-badge`, and shows toasts only for `high`/`critical` priorities.
- The CSS uses `var(--hub-*)` tokens in component rules; literal color values are confined to the `:root` token block.
- The dispatch-referenced paper `papers/browser/15-tutorial-funpack-mcp.md` was not present in this repository, so implementation followed the task spec and existing repo conventions directly.
- Verification witnesses:
  - `pytest -q tests/test_notifications_sse.py`
  - `pytest -q tests/test_yinyang_instructions.py -k 'notifications_list_empty or notifications_unread_count or notifications_mark_all_read_requires_auth or notifications_mark_all_read or notifications_unread_filter or notifications_limit_param or notifications_mark_read'`
  - `python -m py_compile yinyang_server.py`

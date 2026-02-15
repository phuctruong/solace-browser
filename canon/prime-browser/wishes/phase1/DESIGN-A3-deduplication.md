# DESIGN-A3: Request Deduplication + Connection Pooling

**Status:** Design Complete - Ready for Solver
**Depends On:** A1 (per-tab state machine)
**Auth:** 65537

---

## Architecture Overview

The websocket server (`solace_cli/browser/websocket_server.py`) already has basic request tracking via `pending_requests` dict that maps `request_id -> (client_ws, command_type, timestamp)`. A3 extends this with two capabilities:

1. **Request deduplication:** If a command with the same semantic key is already in-flight, return the same future instead of dispatching a duplicate to the extension.
2. **Connection pooling:** Ensure the CLI client (`browser_commands.py`) reuses a single WebSocket connection rather than opening a fresh one per invocation.

---

## Current State Analysis

The existing `websocket_server.py` (lines 33-35) already tracks pending requests:

```python
# Existing code
pending_requests: Dict[str, Tuple[websockets.WebSocketServerProtocol, str, float]] = {}
```

This tracks which client sent which request so responses can be routed back. But it does NOT deduplicate -- if two clients send the same navigate command, both get forwarded to the extension.

The existing `browser_commands.py` creates a new WebSocket connection for every CLI invocation (`connect_to_browser()` on line 46), then closes it when done (line 308). No connection reuse.

---

## Data Structures

### 1. Deduplication Key (Python - in `websocket_server.py`)

```python
from typing import NamedTuple

class DedupKey(NamedTuple):
    """Semantic deduplication key for in-flight requests."""
    command_type: str
    tab_id: int
    payload_hash: str  # Hash of JSON-serialized payload

def make_dedup_key(data: Dict) -> DedupKey:
    """Create deduplication key from command data."""
    cmd_type = data.get("type", "")
    tab_id = data.get("tab_id", 0)
    payload = data.get("payload", {})
    payload_hash = hashlib.md5(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:8]
    return DedupKey(command_type=cmd_type, tab_id=tab_id, payload_hash=payload_hash)
```

### 2. In-Flight Request Tracker (Python - in `websocket_server.py`)

```python
# New: maps dedup_key -> request_id for in-flight dedup lookups
inflight_dedup: Dict[DedupKey, str] = {}

# New: maps request_id -> list of additional client websockets waiting
additional_waiters: Dict[str, List[websockets.WebSocketServerProtocol]] = {}

# Keep existing pending_requests for request_id -> client routing
# pending_requests: Dict[str, Tuple[ws, cmd_type, timestamp]]  # UNCHANGED

# Timeout constant
REQUEST_TIMEOUT_SECONDS = 30
```

### 3. Connection Pool (Python - in `browser_commands.py`)

```python
# Module-level connection cache
_ws_connection: Optional[websockets.WebSocketClientProtocol] = None
```

---

## Key Design Decisions

### D1: Deduplication happens at the server, not the client

- The websocket_server.py sees all incoming commands from all clients
- It can detect when two clients send the same command to the same tab
- Deduplication at this layer prevents redundant work on the extension side
- Client-side dedup is not sufficient (multiple CLI processes don't share state)

### D2: Dedup key includes payload hash, not just command type

- Two NAVIGATE commands to different URLs must NOT be deduplicated
- Two NAVIGATE commands to the same URL on the same tab SHOULD be deduplicated
- The payload hash ensures semantic equivalence

### D3: Deduplication uses fan-out on response

- First request with a given DedupKey dispatches to extension normally
- Subsequent requests with the same key are added as `additional_waiters`
- When the extension responds, the response is sent to both the primary client and all additional waiters
- This is the same pattern used by OpenClaw (RESEARCH_SYNTHESIS.md, line 37-41)

### D4: Connection pooling applies to `browser_commands.py` (client side)

- The server already accepts multiple connections (`websockets.serve`)
- The client (`browser_commands.py`) currently opens a fresh connection per invocation
- Connection pooling means: reuse an existing open connection if available
- This reduces connection overhead for rapid sequential commands

### D5: Request timeout and cleanup

- Inflight requests expire after 30 seconds
- A background cleanup task removes expired entries every 10 seconds
- Prevents memory leaks from abandoned requests

### D6: Dedup is transparent to callers

- `handle_client_command()` returns the same response structure whether the request was deduplicated or not
- The caller never knows if their request was the "original" or a "duplicate"
- A debug log entry indicates when deduplication occurs

---

## Functions to Implement

### In `solace_cli/browser/websocket_server.py`

#### 1. make_dedup_key(data) -> DedupKey

```python
def make_dedup_key(data: Dict) -> DedupKey:
    """Create semantic dedup key from command data."""
    cmd_type = data.get("type", "")
    tab_id = data.get("tab_id", 0)
    payload = data.get("payload", {})
    payload_hash = hashlib.md5(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:8]
    return DedupKey(command_type=cmd_type, tab_id=tab_id, payload_hash=payload_hash)
```

#### 2. send_command_deduplicated(data, client_ws) -> None

```python
async def send_command_deduplicated(data: Dict, client_ws) -> None:
    """Send command to extension, deduplicating in-flight requests.

    If an identical command is already in-flight, the client_ws is added
    as an additional waiter so it receives the same response.
    """
    dedup_key = make_dedup_key(data)

    if dedup_key in inflight_dedup:
        existing_rid = inflight_dedup[dedup_key]
        logger.info(f"   Dedup: {data.get('type')} already in-flight as #{existing_rid}")
        additional_waiters.setdefault(existing_rid, []).append(client_ws)
        return

    # New request -- dispatch normally
    request_id = str(uuid.uuid4())[:8]
    data_with_id = {**data, "request_id": request_id}

    inflight_dedup[dedup_key] = request_id
    pending_requests[request_id] = (client_ws, data.get("type"), asyncio.get_event_loop().time())
    additional_waiters[request_id] = []

    await _forward_to_extensions(data_with_id, request_id, client_ws)
```

#### 3. _forward_to_extensions(data, request_id, client_ws) -> None

```python
async def _forward_to_extensions(data_with_id: Dict, request_id: str, client_ws) -> None:
    """Forward command to all connected extensions. Extracted from handle_client_command."""
    if connected_extensions:
        message = json.dumps(data_with_id)
        failed = []
        for ext_ws in list(connected_extensions):
            try:
                await ext_ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                failed.append(ext_ws)
        for ext_ws in failed:
            connected_extensions.discard(ext_ws)
    else:
        logger.warning("No connected extensions to forward command to")
        pending_requests.pop(request_id, None)
        inflight_dedup_cleanup(request_id)
        await client_ws.send(json.dumps({
            "type": "ERROR",
            "request_id": request_id,
            "error": "No connected extensions"
        }))
```

#### 4. cleanup_expired_requests() -> None

```python
async def cleanup_expired_requests():
    """Background task: remove requests older than REQUEST_TIMEOUT_SECONDS."""
    while True:
        await asyncio.sleep(10)
        now = asyncio.get_event_loop().time()
        expired = [
            rid for rid, (_, _, ts) in pending_requests.items()
            if now - ts > REQUEST_TIMEOUT_SECONDS
        ]
        for rid in expired:
            logger.warning(f"   Timeout: request #{rid} expired after {REQUEST_TIMEOUT_SECONDS}s")
            pending_requests.pop(rid, None)
            inflight_dedup_cleanup(rid)
            additional_waiters.pop(rid, None)
```

#### 5. inflight_dedup_cleanup(request_id) -> None

```python
def inflight_dedup_cleanup(request_id: str) -> None:
    """Remove dedup entries pointing to a completed/expired request_id."""
    to_remove = [k for k, v in inflight_dedup.items() if v == request_id]
    for k in to_remove:
        del inflight_dedup[k]
```

#### 6. Modify handle_message() for fan-out + dedup cleanup

In the existing response routing logic, after sending to the primary client:

```python
# After sending response to primary client via pending_requests[request_id]:
# Fan out to additional waiters
waiters = additional_waiters.pop(request_id, [])
for waiter_ws in waiters:
    try:
        await waiter_ws.send(json.dumps(data))
    except websockets.exceptions.ConnectionClosed:
        pass

# Clean up dedup tracking
inflight_dedup_cleanup(request_id)
```

### In `solace_cli/cli/browser_commands.py`

#### 7. get_pooled_connection(url) -> WebSocket

```python
_ws_connection = None

async def get_pooled_connection(url: str = "ws://localhost:9222"):
    """Get or create a single WebSocket connection (connection pooling)."""
    global _ws_connection

    if _ws_connection is not None:
        try:
            await _ws_connection.ping()
            return _ws_connection
        except Exception:
            _ws_connection = None

    if not preflight_check():
        logger.error("Server not reachable at ws://localhost:9222")
        return None

    try:
        _ws_connection = await asyncio.wait_for(
            websockets.connect(url), timeout=5
        )
        return _ws_connection
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        _ws_connection = None
        return None
```

---

## Integration Points

### File: `solace_cli/browser/websocket_server.py` (MODIFY)

- Add `DedupKey` namedtuple, `inflight_dedup`, `additional_waiters` dicts
- Add `REQUEST_TIMEOUT_SECONDS = 30` constant
- Add `make_dedup_key()`, `send_command_deduplicated()`, `_forward_to_extensions()`, `inflight_dedup_cleanup()`, `cleanup_expired_requests()` functions
- Replace direct forwarding in `handle_client_command()` with call to `send_command_deduplicated()`
- Add fan-out + cleanup logic in `handle_message()` response routing
- Start `cleanup_expired_requests()` as background task in `start_server()`

### File: `solace_cli/cli/browser_commands.py` (MODIFY)

- Add `get_pooled_connection()` function
- Replace `connect_to_browser()` with `get_pooled_connection()` in `main()`
- Keep `connect_to_browser()` as fallback (do not delete yet)

---

## Files to Create/Modify

| File | Action | LOC |
|------|--------|-----|
| `solace_cli/browser/websocket_server.py` | MODIFY | +120 |
| `solace_cli/cli/browser_commands.py` | MODIFY | +30 |
| **Total** | | **~150 LOC net** |

---

## Function Inventory

| Function | File | Purpose |
|----------|------|---------|
| `make_dedup_key(data)` | websocket_server.py | Create semantic dedup key |
| `send_command_deduplicated(data, ws)` | websocket_server.py | Deduplicated command dispatch |
| `_forward_to_extensions(data, rid, ws)` | websocket_server.py | Extracted forwarding logic |
| `inflight_dedup_cleanup(rid)` | websocket_server.py | Clean dedup tracking for a request |
| `cleanup_expired_requests()` | websocket_server.py | Background timeout cleanup |
| `get_pooled_connection(url)` | browser_commands.py | Connection pool for clients |

---

## Complexity Assessment

- **Difficulty:** Medium
- **Risk:** Medium (concurrent dedup requires careful shared state handling)
- **Day estimate:** 1.5 days
- **Dependencies:** A1 (tab_id field in commands for proper dedup key construction)

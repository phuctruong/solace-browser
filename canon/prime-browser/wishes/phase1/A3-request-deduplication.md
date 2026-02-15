# Wish A3: Request Deduplication + Connection Pooling

**Task ID:** A3
**Phase:** Phase A (Parity with OpenClaw)
**Owner:** Solver (via Haiku swarm)
**Timeline:** 2 days
**Depends On:** A1 (per-tab state machine)
**Status:** READY FOR EXECUTION
**Auth:** 65537

---

## Specification

Implement efficient request deduplication and connection pooling for WebSocket relay. Prevents duplicate CDP commands and ensures single WebSocket connection per relay server.

**Reference Pattern:** OpenClaw deduplication (RESEARCH_SYNTHESIS.md, line 37–41)

---

## Requirements

### Request Deduplication

```python
# Map to track pending requests
pending_requests: Dict[str, Dict] = {}  # requestId → {resolve, reject, timestamp}

def send_command_deduplicated(request_id: str, command: Dict) -> Any:
    """Send command, deduplicate if already pending"""

    # Check if request already in flight
    if request_id in pending_requests:
        log(f"Deduplicating request {request_id}")
        return pending_requests[request_id]

    # Create promise-like structure
    future = asyncio.Future()
    pending_requests[request_id] = {
        'future': future,
        'command': command,
        'timestamp': now()
    }

    try:
        # Send via WebSocket
        result = await websocket.send(command)
        future.set_result(result)
    except Exception as e:
        future.set_exception(e)
    finally:
        del pending_requests[request_id]

    return future
```

### Connection Pooling

```python
# Single relay connection (reuse, don't reconnect)
relay_connection: Optional[WebSocket] = None
relay_connect_promise: Optional[asyncio.Future] = None

async def get_relay_connection(relay_url: str) -> WebSocket:
    """Get or create single connection to relay"""
    global relay_connection, relay_connect_promise

    # If connection exists and healthy, reuse it
    if relay_connection and relay_connection.open:
        return relay_connection

    # If connection in progress, wait for it
    if relay_connect_promise:
        return await relay_connect_promise

    # Create new connection
    relay_connect_promise = asyncio.Future()
    try:
        relay_connection = await websockets.connect(relay_url)
        relay_connect_promise.set_result(relay_connection)
        return relay_connection
    except Exception as e:
        relay_connect_promise.set_exception(e)
        relay_connection = None
        raise
    finally:
        relay_connect_promise = None
```

### Integration Points

1. **solace_cli/websocket_server.py**
   - Add `pending_requests` dict
   - Add `send_command_deduplicated()` function
   - Add `get_relay_connection()` function
   - Replace all WebSocket sends with deduplicated version

2. **solace_cli/browser_commands.py**
   - Use `send_command_deduplicated()` for all CDP commands
   - Pass unique `request_id` (generated or user-provided)

---

## Success Criteria (641-Edge)

✅ **DUP1:** Identical requests with same ID deduplicated
- send_command("req_123", navigate_command)
- send_command("req_123", navigate_command) → returns same future

✅ **DUP2:** Different request IDs not deduplicated
- send_command("req_123", navigate_command)
- send_command("req_124", navigate_command) → both execute

✅ **POOL1:** Single WebSocket per relay
- 100 commands → only 1 WebSocket connection created
- Connection reused for all commands

✅ **POOL2:** Connection reconnection on failure
- WebSocket closes → next command reconnects automatically
- No manual reconnection required

✅ **POOL3:** Concurrent deduplication safe
- 10 threads send same request_id simultaneously
- Only 1 command actually sent, all 10 get same result

---

## Implementation Checklist

- [ ] Add `pending_requests` dictionary to `websocket_server.py`
- [ ] Implement `send_command_deduplicated(request_id, command)` function
- [ ] Add connection pooling logic with `relay_connect_promise`
- [ ] Update `get_relay_connection(relay_url)` function
- [ ] Add request timeout + cleanup (< 30s)
- [ ] Test deduplication of identical request IDs
- [ ] Test non-deduplication of different request IDs
- [ ] Test single connection for multiple commands
- [ ] Test connection reconnection on failure
- [ ] Test concurrent deduplication safety (threading)

---

## Acceptance Criteria

✅ Duplicate requests rejected, return same result
✅ Only 1 WebSocket per relay (verified by connection count)
✅ Connection pooling + reuse working
✅ Automatic reconnection on failure
✅ Thread-safe concurrent deduplication
✅ 641-edge tests pass (all 5 dedup/pool cases)
✅ 274177-stress tests pass (100+ concurrent commands)
✅ OpenClaw pattern matched exactly

---

## Related Skills

- `browser-state-machine.md` v1.0.0 (state validation)

---

## Performance Targets

- ✅ Deduplication check: < 1ms
- ✅ Connection reuse: < 5ms
- ✅ Command dispatch: < 50ms

---

**Ready to assign to:** Solver (implementation after A1)

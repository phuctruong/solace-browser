# Diagram 08: Four-Plane Browser Architecture
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 05 (PZip), Paper 06 (Evidence), Paper 03 (Web-Native)

---

## Four Independent Planes

```mermaid
graph TB
    subgraph "CAPTURE PLANE — always on"
        CAP_G["Guest: HTML only\n(local, no sync)"]
        CAP_L["Logged-in: Full pipeline\nPrime Mermaid + PZip + RTC"]
    end

    subgraph "CONTROL PLANE — Bearer sw_sk_ required"
        CTRL["JSON-RPC over WS\nPOST /rpc\nTunnel: same protocol"]
    end

    subgraph "EXECUTION PLANE — OAuth3 scoped"
        EXEC["Recipe executor\nLLM ONCE at preview\nCPU replay at execution"]
    end

    subgraph "EVIDENCE PLANE — always on"
        EVID_B["Basic: local hash chain"]
        EVID_P["Part 11: ALCOA+ chain\n+ e-signatures\n+ cloud vault sync"]
    end

    style CAP_G fill:#2d7a2d,color:#fff
    style CAP_L fill:#2d7a2d,color:#fff
    style CTRL fill:#1a5cb5,color:#fff
    style EXEC fill:#1a5cb5,color:#fff
    style EVID_B fill:#2d7a2d,color:#fff
    style EVID_P fill:#7a2d7a,color:#fff
```

## Plane Independence

| Plane | Auth | Internet | PZip |
|-------|------|----------|------|
| Capture (guest) | No | No | No |
| Capture (logged) | Yes | Yes (sync) | Yes |
| Control | Yes | No (local) / Yes (tunnel) | No |
| Execution | Yes | No (local) / Yes (cloud) | No |
| Evidence (basic) | No | No | No |
| Evidence (Part 11) | Yes | Yes (vault sync) | Yes |

## Invariants

1. Each plane operates independently — failure in one does not affect others
2. Capture plane works offline, always (guest mode)
3. Control plane requires Bearer sw_sk_ on every request
4. Execution plane calls LLM ONCE at preview, NEVER during execution
5. Evidence plane captures at event time, never retroactively

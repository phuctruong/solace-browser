---
id: diagram-70-browser-server-architecture
type: diagram
added_at: 2026-02-24
title: "Solace Browser Server Control Architecture"
persona: Tim Berners-Lee
related: [browser-multi-layer-architecture, twin-sync-flow]
---

# Diagram 70: Browser Server Webservice Control Architecture

## Diagram 1: Startup Flow

```mermaid
flowchart TD
    A[solace-browser-server.sh] --> B[Resolve mode: headless or headed]
    B --> C[Start browser core]
    C --> D[Start API server :9222]
    C --> E[Start UI server :9223]
    D --> F[Attach OAuth3 middleware]
    D --> G[Expose control endpoints]
    D --> H[Register tunnel listener]
    D --> I[Register with stillwater admin]
```

## Diagram 2: Control Modes

```mermaid
flowchart LR
    H0[HEADLESS default] --> C0[API-first automation]
    H1[HEADED --head] --> C1[Visible browser + intervention]
    H2[CLOUD TWIN] --> C2[Cloud Run headless execution]
    H3[TUNNEL] --> C3[Remote agent controls local browser]
```

## Diagram 3: Integration with 4-mode Self-Service

```mermaid
flowchart TB
    subgraph M1[Mode 1 Cloud-only]
      M1A[solaceagi.com API] --> M1B[Cloud browser server]
    end

    subgraph M2[Mode 2 Local-only]
      M2A[Local CLI] --> M2B[Local browser server]
    end

    subgraph M3[Mode 3 Hybrid-A]
      M3A[Local CLI] --> M3B[Cloud browser server]
    end

    subgraph M4[Mode 4 Hybrid-B]
      M4A[solaceagi.com API] --> M4B[Local browser server via tunnel]
    end
```

## Invariants

- API and UI are separate processes (`9222` API, `9223` UI).
- OAuth3 scope checks gate all privileged browser actions.
- Tunnels are explicit, revocable, and auditable.
- Headed/headless mode is selected at startup and visible via status API.

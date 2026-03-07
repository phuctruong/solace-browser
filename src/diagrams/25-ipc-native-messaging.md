# Diagram 25: IPC / Native Messaging Flow
# DNA: `tauri(spawn) -> nm_host(bootstrap) -> extension(token) -> ws(connected) = secure_ipc`
**Paper:** 47, 48 (sidebar + companion) | **Auth:** 65537

---

## Token Bootstrap via Native Messaging

```mermaid
sequenceDiagram
    participant Tauri as Companion App (Tauri)
    participant Python as Python Backend
    participant NM as Native Messaging Host
    participant SW as Extension Service Worker
    participant Panel as Side Panel
    participant WS as WebSocket

    Note over Tauri: User launches Solace
    Tauri->>Python: Spawn as child process
    Python->>Python: Generate SOLACE_SESSION_SECRET<br/>(secrets.token_urlsafe(32))
    Python->>Python: Write port to ~/.solace/port.lock
    Tauri->>NM: Install NM host manifest<br/>(com.solaceagi.bridge.json)

    Note over SW: Extension loads in Chromium
    SW->>NM: chrome.runtime.connectNative("com.solaceagi.bridge")
    NM->>NM: Read port from ~/.solace/port.lock
    NM->>NM: Read token from Tauri keychain
    NM-->>SW: {port: 8888, token: "...", tokenGeneration: 1}
    SW->>SW: chrome.storage.session.set({token, port})

    Note over Panel: Side panel opens
    Panel->>SW: Request token via chrome.runtime.sendMessage
    SW-->>Panel: {token, port} from session storage
    Panel->>WS: Connect ws://localhost:8888/ws/yinyang<br/>+ X-Solace-Token header
    WS-->>Panel: {type: "hello", serverVersion: "1.0.0"}

    Note over Tauri,WS: Token Rotation
    Python->>Python: Restart (new token, tokenGeneration++)
    Panel->>Python: Health check returns tokenGeneration mismatch
    Panel->>SW: Request fresh token
    SW->>NM: Re-query Native Messaging host
    NM-->>SW: {port: 8888, token: "NEW", tokenGeneration: 2}
    SW-->>Panel: New token
    Panel->>WS: Reconnect with new token
```

## Security Boundaries

```mermaid
graph TB
    subgraph Trusted ["Trusted Zone (localhost only)"]
        TAURI[Companion App<br/>Rust / Tauri]
        PYTHON[Python Backend<br/>aiohttp]
        NM[Native Messaging Host<br/>Bundled binary]
    end

    subgraph Extension ["Extension Zone (Chrome sandbox)"]
        SW[Service Worker<br/>MV3]
        PANEL[Side Panel<br/>HTML/JS]
    end

    subgraph Untrusted ["Untrusted Zone"]
        PAGE[Web Pages<br/>gmail.com etc]
        MALICIOUS[Malicious local<br/>process]
    end

    TAURI -->|"spawn + SIGTERM"| PYTHON
    TAURI -->|"install manifest"| NM
    NM -->|"port + token"| SW
    SW -->|"session storage"| PANEL
    PANEL -->|"X-Solace-Token"| PYTHON
    PYTHON -->|"origin check"| PANEL

    MALICIOUS -.->|"blocked: no token"| PYTHON
    PAGE -.->|"blocked: wrong origin"| PYTHON
    PAGE -.->|"isolated"| PANEL

    style Trusted fill:#2ecc71,stroke:#2ecc71,color:#000
    style Extension fill:#6C5CE7,stroke:#6C5CE7,color:#fff
    style Untrusted fill:#e74c3c,stroke:#e74c3c,color:#fff
```

## Process Lifecycle

```mermaid
stateDiagram-v2
    [*] --> TauriStart: User launches Solace

    TauriStart --> SpawnPython: Spawn child process
    SpawnPython --> HealthCheck: Python running

    HealthCheck --> Healthy: GET /health OK
    HealthCheck --> Retry: GET /health FAIL
    Retry --> SpawnPython: Attempt 1-3 (backoff)
    Retry --> Error: 3 failures

    Healthy --> HealthCheck: Every 30s
    Healthy --> Crash: Python exits non-zero
    Crash --> SpawnPython: Auto-restart

    Error --> TauriNotify: Show tray error

    Healthy --> TauriQuit: User quits
    TauriQuit --> SIGTERM: Send to Python
    SIGTERM --> Wait3s: Grace period
    Wait3s --> SIGKILL: Force kill
    SIGKILL --> CleanPorts: Delete port.lock
    CleanPorts --> [*]
```

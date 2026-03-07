# Diagram 24: Sidebar Tab Flow
# DNA: `now(detect) + runs(history) + chat(converse) + more(settings) = 4_tabs_not_20_pages`
**Paper:** 47 (yinyang-sidebar-architecture) | **Auth:** 65537

---

## Tab State Machine

```mermaid
stateDiagram-v2
    [*] --> Now: Default tab on open

    Now --> Runs: User clicks "Runs" tab
    Now --> Chat: User clicks "Chat" tab
    Now --> More: User clicks "More" tab

    Runs --> Now: User clicks "Now" tab
    Runs --> Chat: User clicks "Chat" tab
    Runs --> More: User clicks "More" tab

    Chat --> Now: User clicks "Now" tab
    Chat --> Runs: User clicks "Runs" tab
    Chat --> More: User clicks "More" tab

    More --> Now: User clicks "Now" tab
    More --> Runs: User clicks "Runs" tab
    More --> Chat: User clicks "Chat" tab

    Now --> Runs: Auto-switch on "Run Now" click

    state Now {
        [*] --> DetectApps
        DetectApps --> ShowApps: matches found
        DetectApps --> EmptyState: no matches
        ShowApps --> RunStarted: "Run Now" clicked
    }

    state Runs {
        [*] --> ApprovalQueue
        ApprovalQueue --> RecentRuns
    }

    state Chat {
        [*] --> ChatReady
        ChatReady --> Sending: user sends message
        Sending --> ChatReady: response received
    }
```

## App Detection Flow

```mermaid
sequenceDiagram
    participant Page as Web Page
    participant SW as Service Worker
    participant Cache as Session Storage
    participant Panel as Side Panel
    participant API as localhost:8888

    Page->>SW: chrome.tabs.onUpdated (URL changed)
    SW->>Cache: Check cached app manifests
    alt Cache hit (< 60s old)
        Cache-->>SW: Return cached apps
    else Cache miss
        SW->>API: GET /api/apps
        API-->>SW: App catalog
        SW->>Cache: Store with timestamp
    end
    SW->>SW: Match URL against app manifests
    SW->>SW: Update badge count
    SW->>Cache: Store matched_{tabId}
    Panel->>SW: GET_MATCHED_APPS message
    SW->>Cache: Read matched_{tabId}
    Cache-->>SW: App IDs
    SW-->>Panel: {apps: [...], url: "..."}
    Panel->>Panel: Render app cards in "Now" tab
```

## Run App Flow

```mermaid
sequenceDiagram
    participant User
    participant Panel as Side Panel
    participant WS as WebSocket
    participant Server as localhost:8888
    participant Browser as Playwright

    User->>Panel: Click "Run Now" on app card
    Panel->>WS: {type: "run", app_id: "gmail-triage"}
    WS->>Server: Start recipe execution
    Server->>Browser: Navigate, extract, process
    Server-->>WS: {type: "state", state: "PREVIEW_READY", preview: "..."}
    WS-->>Panel: Show preview + Approve/Reject
    User->>Panel: Click "Approve"
    Panel->>WS: {type: "approve", run_id: "abc123"}
    WS->>Server: Execute approved steps
    Server->>Browser: Execute with evidence capture
    loop Each step
        Server-->>WS: {type: "state", step: N, status: "running"}
        WS-->>Panel: Update progress
    end
    Server-->>WS: {type: "state", state: "COMPLETE", cost: 0.08}
    WS-->>Panel: Show completion + evidence link
```

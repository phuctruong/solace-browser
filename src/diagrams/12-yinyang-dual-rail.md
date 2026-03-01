# Diagram 12: Yinyang Dual Rail — Integration with Apps
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 04 (Yinyang), solace-cli/diagrams/13-yinyang-fsm.md

---

## Dual Rail Layout

```mermaid
graph TB
    subgraph "Top Rail (32px — Status)"
        TR["☯ | STATE_DOT | Step 2/5 | $0.003 | [⏸]"]
    end

    subgraph "Bottom Rail (36px collapsed / 300px expanded)"
        BR_C["☯ Yinyang | $3.47 | Yellow Belt | [▲]"]
        BR_E["Chat transcript\n+ Approve/Edit/Reject\n+ [📁 VS Code] [Send]"]
    end

    subgraph "Visibility Rules"
        IDLE["Idle: Top=HIDDEN, Bottom=COLLAPSED"]
        RUN["Running: Top=VISIBLE, Bottom=user pref"]
        PREVIEW["Preview Ready: Top=AMBER, Bottom=AUTO-EXPAND"]
        ERROR["Error: Top=RED, Bottom=AUTO-EXPAND"]
        DONE["Done: Top=fades→HIDDEN, Bottom=summary→collapse 30s"]
    end

    style TR fill:#222,color:#fff
    style BR_C fill:#1a5cb5,color:#fff
    style BR_E fill:#1a5cb5,color:#fff
```

## App Integration Flow

```mermaid
sequenceDiagram
    participant U as User
    participant BR as Bottom Rail
    participant TR as Top Rail
    participant APP as App Engine
    participant FSM as Yinyang FSM

    U->>BR: "Triage my Gmail"
    BR->>FSM: IDLE → LISTENING
    FSM->>TR: Show: ☯ LISTENING
    FSM->>APP: Start gmail-inbox-triage
    FSM->>TR: Show: ☯ PROCESSING | Scanning...
    APP->>FSM: Preview generated (42 emails)
    FSM->>TR: Show: ☯ PREVIEW_READY (amber)
    FSM->>BR: AUTO-EXPAND with preview
    BR->>U: Show: Archive 28, Star 5, Draft 3
    BR->>U: [✓ Approve] [✏️ Edit] [✗ Reject]
    U->>BR: Click [Approve]
    FSM->>FSM: APPROVED → SEALED → COOLDOWN (5s)
    FSM->>TR: Show: ☯ EXECUTING | Step 1/3...
    APP->>FSM: All steps done
    FSM->>TR: Show: ☯ DONE (fades 5s)
    FSM->>BR: Show summary + report link
    Note over BR: Auto-collapse after 30s
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Y / Cmd+Y | Toggle bottom rail |
| Ctrl+Shift+Y | Focus input |
| Escape | Collapse |
| Enter (preview) | Approve |
| Ctrl+. | Pause execution |

## Invariants

1. Top rail = status ONLY (never chat, never forms)
2. Bottom rail = user-summoned for chat (never auto-opens for chat)
3. Auto-expand ONLY for: PREVIEW_READY, BLOCKED, ERROR
4. PREVIEW_READY → APPROVED requires explicit user click
5. Collapse preference persists across sessions
6. Zero forms, toggles, or inputs (except chat input)

# Diagram 42: Solace Inspector — Agent-Native HITL QA System
# Committee: James Bach · Elisabeth Hendrickson · Kent Beck · Cem Kaner · Michael Bolton
# Auth: 65537 | GLOW: L | Date: 2026-03-03
# Architecture: Agent-native (zero LLM API calls — $0.00/run)

## Overview — The Full HITL Loop

```mermaid
flowchart TD
    subgraph Agents["🤖 AI Coding Agents (Claude Code/Codex/Cursor/Gemini)"]
        A[Agent reads codebase\nfinds potential issue] --> B[Write test-spec-*.json\nto inbox/]
        B --> C[Wait for sealed report\nin outbox/]
        C --> D[Read report:\nqa_score + agent_analysis_request]
        D --> E[Agent applies OWN model\nfills agent_analysis_response]
        E --> F[Propose fixes\nappend to report.fix_proposals]
    end

    subgraph Inspector["🔍 Solace Inspector — Evidence Engine"]
        G[Poll inbox/\nfor new specs] --> H[Step 1: Navigate to URL]
        H --> I[Step 2: ARIA Snapshot\naccessibility tree]
        I --> J[Step 3: DOM Snapshot\nlinks/images/forms]
        J --> K[Step 4: Heuristic Check\nHICCUPPS + ARIA violations]
        K --> L[Step 5: Full Screenshot\nvisual evidence]
        L --> M["Step 6: Build agent_analysis_request\n(persona prompt + raw evidence)\n💲$0.00 — agent applies own model"]
        M --> N[Step 7: Compute Score\nqa_score + belt + GLOW]
        N --> O[Step 8: Seal Report\nSHA-256 + outbox/]
    end

    subgraph Human["👤 Human (One Click)"]
        P[Review fix_proposals\nin dashboard] --> Q{Approve?}
        Q -->|✅ Yes| R[Click e-sign\nApprove Fix]
        Q -->|❌ No| S[Write feedback\nback to inbox/]
        R --> T[Agent implements\napproved fix]
        T --> G
    end

    subgraph Vault["🔐 Evidence Vault (FDA Part 11)"]
        U[outbox/report-*.json\nSHA-256 sealed] --> V[Sync to cloud\nsolaceagi.com/qa-evidence]
        V --> W[Public QA Dashboard\nchange logs + certs]
    end

    B --> G
    O --> P
    O --> U
    F --> P
```

## The Agent-Native Architecture

```mermaid
sequenceDiagram
    participant Agent as 🤖 Claude Code (AI Agent)
    participant Inbox as 📥 inbox/
    participant Runner as 🔍 run_solace_inspector.py
    participant Outbox as 📤 outbox/
    participant Human as 👤 Human
    participant Vault as 🔐 Evidence Vault

    Note over Agent,Vault: Agent-Native: Runner collects evidence. Agent provides analysis.

    Agent->>Inbox: Write test-spec-001.json<br/>{target_url, persona:"james_bach", checks}
    Runner->>Inbox: Poll — spec found
    Runner->>Runner: Step 1: Navigate to URL
    Runner->>Runner: Step 2: ARIA snapshot
    Runner->>Runner: Step 3: DOM snapshot
    Runner->>Runner: Step 4: HICCUPPS heuristics → 3 issues found
    Runner->>Runner: Step 5: Full screenshot
    Runner->>Runner: "Step 6: Build agent_analysis_request $0.00"
    Note over Runner: NO API call. Persona prompt + evidence bundled.
    Runner->>Runner: Step 7: QA Score = 74 (Yellow belt)
    Runner->>Outbox: report-001.json<br/>{score:74, 3 issues, agent_analysis_request, sha256}
    Runner->>Vault: Sealed record written

    Agent->>Outbox: Read report
    Note over Agent: Agent sees agent_analysis_request with<br/>James Bach system prompt + all evidence
    Agent->>Agent: Apply own model → James Bach analysis
    Agent->>Outbox: Update report:<br/>agent_analysis_response + fix_proposals

    Agent->>Human: "Found 3 issues. Proposing 2 fixes."
    Human->>Human: Review fix_proposals
    Human->>Runner: POST /api/v1/esign (approve fix)
    Runner->>Outbox: report updated: human_approved=true

    Agent->>Agent: Implement approved fix
    Agent->>Inbox: test-spec-002.json (re-check)
    Runner->>Outbox: report-002.json {score:89, 0 errors}
    Human->>Human: "Yellow → Orange! 🎉 Evidence sealed."
```

## 10 Uplift Injection Points (Paper 17)

```mermaid
mindmap
  root((Solace\nInspector))
    P1 Gamification
      QA Score 0-100
      Belt White→Green
      GLOW per run
      STATUS.md tracker
    P2 Magic Words
      /qa-inspect
      /qa-baseline
      /qa-diff
      /qa-seal
      /qa-esign
    P3 Famous Personas
      James Bach SBTM+HICCUPPS
      Cem Kaner BBST
      Elisabeth Hendrickson Explore It
      Kent Beck TDD+testability
      Michael Bolton RST
    P4 Skills
      HICCUPPS oracle heuristics
      SBTM session management
      Charter-based exploration
      TDD testability lens
    P5 Recipes
      8-step web recipe
      7-step CLI recipe
      8-step API recipe
      Replay at $0.001
    P6 Access Tools
      browser.navigate
      browser.screenshot
      aria_snapshot
      cli.execute
      api.request
    P7 Memory
      SHA-256 evidence vault
      Baseline snapshots
      Diff detection
      outbox/ persistent store
    P8 Care
      Human-readable reports
      Anti-Clippy always
      Warm language
      Fix proposals = proposals
    P9 Knowledge
      Paper 42 this paper
      Paper 02 inbox/outbox
      Paper 40 FDA evidence
      Paper 06 ALCOA+
    P10 God
      SHA-256 every report
      FDA 21 CFR Part 11
      GLOW target 65537
      Evidence is truth
```

## Self-Diagnostic Flow (Daily Health Check)

```mermaid
flowchart LR
    subgraph Cron["⏰ Daily @ 08:00"]
        CRON[run_solace_inspector.py\n--self-diagnostic]
    end
    subgraph Pages["🌀 Solace Browser Pages"]
        HOME[localhost:8791/]
        STORE[localhost:8791/app-store]
        SETT[localhost:8791/settings]
        SCHED[localhost:8791/schedule]
        START[localhost:8791/start]
    end
    subgraph Reports["📊 QA Reports"]
        R1[report-home-*.json]
        R2[report-store-*.json]
        R3[report-settings-*.json]
        R4[report-schedule-*.json]
        R5[report-start-*.json]
        SUMMARY[self-diag-YYYYMMDD.json\nOverall belt + GLOW]
    end

    CRON --> HOME & STORE & SETT & SCHED & START
    HOME --> R1
    STORE --> R2
    SETT --> R3
    SCHED --> R4
    START --> R5
    R1 & R2 & R3 & R4 & R5 --> SUMMARY
```

## Competitive Position (Confirmed March 2026)

```mermaid
xychart-beta
    title "QA Tool Comparison"
    x-axis ["Solace Inspector", "Playwright MCP", "Ketryx", "QA Wolf", "Mabl", "TestRigor"]
    y-axis "Feature Count (max 3)" 0 --> 3
    bar [3, 1, 2, 0.5, 0, 1]
```

> Agent Protocol (1pt) + Evidence Chain (1pt) + Human E-Sign (1pt) = 3/3 only Solace Inspector

# Diagram 02: Inbox as QA Memory Substrate
# Solace Inspector | Auth: 65537 | GLOW: L | Updated: 2026-03-03
# Replaces: Jira · Asana · Notion boards · spreadsheets

## Inbox = The Official QA Board

```mermaid
flowchart LR
    subgraph Traditional["❌ Traditional QA (Jira/Kanban)"]
        T1[Ticket created\nin Jira] --> T2[Test executed\n'somewhere']
        T2 --> T3[Result noted\nin comment]
        T3 --> T4[Evidence:\n'I tested it'\n— zero value in\nregulated industries]
    end

    subgraph Inspector["✅ Solace Inspector Inbox"]
        I1["inbox/test-spec-*.json\n= Jira ticket\n+ test case\n+ charter\n+ persona"] --> I2[Inspector runs\nseals evidence]
        I2 --> I3["outbox/report-*.json\n= SHA-256 sealed\nPart 11 ready\ncourt-admissible"]
        I3 --> I4["100/100 Green\n= sprint done\n= ticket closed"]
    end

    style Traditional fill:#2d0000,stroke:#ff6b6b,color:#fff
    style Inspector fill:#0d2b0d,stroke:#52b788,color:#fff
```

## 62 Standing Specs = 62 QA Contracts (GLOW 99)

```
Spec Category          Count   Persona(s)            Belt Target
─────────────────────────────────────────────────────────────────
API health/version       2     Kent Beck             100/100
API auth (401 guard)     3     James Bach            100/100
API billing protect      2     Kent Beck             100/100
API LLM endpoints        2     Kent Beck             100/100
OWASP adversarial        5     Bach + Kaner          100/100
solaceagi.com pages     20     Hendrickson           100/100
solace-browser pages     8     Hendrickson           100/100
Paper claim verify       4     Michael Bolton        100/100
YinYang API + MCP        5     Cem Kaner             100/100
Fun pack locales         1     Hendrickson           100/100
Architecture specs       5     James Bach            100/100
SOP docs                 5     Kaner + Bach          100/100
─────────────────────────────────────────────────────────────────
TOTAL                   62     5-member committee    62/62 Green
```

## The Sprint Metaphor

```
Jira Sprint             Inspector Inbox
─────────────────────── ───────────────────────
Open ticket      →      JSON spec in inbox/
Work in progress →      Inspector running
Done             →      100/100 Green in outbox/
Closed/verified  →      SHA-256 sealed report
Sprint complete  →      All 62 specs Green
```

## Retention (Part 11 Ready)

- **outbox/**: append-only, never delete
- **SHA-256**: every report sealed at creation
- **Human approvals**: HITL record in fix_proposals
- **Audit trail**: complete chain from spec → finding → fix → approval

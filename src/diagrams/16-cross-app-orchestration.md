# Diagram 16: Cross-App Orchestration
**Paper:** 08-cross-app-yinyang-delight | **Auth:** 65537

## Cross-App Message Flow

```mermaid
flowchart TD
    subgraph APP_A["App A (gmail-inbox-triage)"]
        A_EXEC[Execute recipe] --> A_OUT[outbox/suggestions/notify-slack.json]
    end

    subgraph ORCH["Orchestrator Layer"]
        A_OUT --> VALIDATE{Validate}
        VALIDATE -->|partner check| B6{B6: Cross-App Gate}
        B6 -->|target installed + budget > 0| DELIVER[Drop into target inbox]
        B6 -->|fail| BLOCKED[BLOCKED — evidence sealed]
    end

    subgraph APP_B["App B (slack-triage)"]
        DELIVER --> B_IN[inbox/requests/from-gmail-run123.json]
        B_IN --> B_EXEC[Execute request]
        B_EXEC --> B_OUT[outbox/runs/run456/]
    end

    subgraph EVIDENCE["Evidence Chain (unbroken)"]
        A_EXEC -.->|step 1-2| CHAIN[workflow_evidence_chain.jsonl]
        B_EXEC -.->|step 3-4| CHAIN
        CHAIN --> SEAL[Evidence sealed with cross-app run_id]
    end
```

## Partner Discovery

```mermaid
flowchart LR
    subgraph MANIFEST["manifest.yaml"]
        PRODUCES[produces_for: slack, drive, calendar]
        CONSUMES[consumes_from: morning-brief, linkedin]
        DISCOVERS[discovers: category=comms, tag=email]
    end

    PRODUCES --> REGISTRY{App Registry}
    CONSUMES --> REGISTRY
    DISCOVERS --> REGISTRY
    REGISTRY --> MATCHED[Matched partner apps]
    MATCHED --> BUDGET_CHECK[Budget gate B6]
```

## Orchestrator App Pattern

```mermaid
flowchart TD
    TRIGGER[Morning Brief triggered] --> PARALLEL

    subgraph PARALLEL["Parallel Execution (budget-gated)"]
        GMAIL[gmail-inbox-triage]
        CAL[calendar-brief]
        GITHUB[github-issue-triage]
        SLACK[slack-triage]
    end

    GMAIL --> COLLECT[Collect all outbox results]
    CAL --> COLLECT
    GITHUB --> COLLECT
    SLACK --> COLLECT

    COLLECT --> LLM["LLM ONCE: synthesize"]
    LLM --> REPORT[outbox/reports/morning-brief-2026-03-01.md]
    REPORT --> YINYANG[Surface in Yinyang bottom rail]
```

## Budget Gate B6 (Cross-App)

```mermaid
flowchart TD
    REQ[Cross-app request] --> B6_1{Target app installed?}
    B6_1 -->|no| BLOCK[BLOCKED]
    B6_1 -->|yes| B6_2{Target in partners list?}
    B6_2 -->|no| BLOCK
    B6_2 -->|yes| B6_3{Target budget > 0?}
    B6_3 -->|no| BLOCK
    B6_3 -->|yes| B6_4["Effective budget = MIN(source, target)"]
    B6_4 --> DELIVER[Deliver to target inbox]
    BLOCK --> EVIDENCE[Evidence sealed: BLOCKED]
```

## Required App Directory Structure

```mermaid
flowchart TD
    APP["~/.solace/apps/{app-id}/"]
    APP --> M[manifest.yaml]
    APP --> R[recipe.json]
    APP --> B[budget.json]
    APP --> D["diagrams/ (REQUIRED)"]
    D --> DW[workflow.md]
    D --> DD[data-flow.md]
    D --> DP[partner-contracts.md]
    APP --> IN[inbox/]
    IN --> PROMPTS[prompts/]
    IN --> TEMPLATES[templates/]
    IN --> ASSETS[assets/]
    IN --> POLICIES[policies/]
    IN --> DATASETS[datasets/]
    IN --> REQUESTS[requests/ — cross-app incoming]
    IN --> CONV["conventions/"]
    CONV --> CONFIG[config.yaml]
    CONV --> DEFAULTS[defaults.yaml]
    CONV --> EXAMPLES[examples/]
    APP --> OUT[outbox/]
    OUT --> PREVIEWS[previews/]
    OUT --> DRAFTS[drafts/]
    OUT --> REPORTS[reports/]
    OUT --> SUGGESTIONS[suggestions/ — cross-app outgoing]
    OUT --> RUNS["runs/{run-id}/"]
```

# Diagram 11: Source-Available Licensing Architecture
# Auth: 65537 | Created: 2026-03-04 GLOW 122
# DNA: license(safety) = transparency × control × time_release → trust

## Three-Tier Licensing Model

```mermaid
graph TD
    subgraph PUBLIC["PUBLIC (OSS — MIT)"]
        ST[stillwater<br/>Verification OS]
        PA[paudio<br/>Speech Synthesis]
        PN[phucnet<br/>Personal Site]
        IF[if<br/>Physics Research]
        PZ[pzip<br/>Compression]
    end

    subgraph SOURCE["SOURCE-AVAILABLE (FSL)"]
        SB[solace-browser<br/>OAuth3 Reference Impl<br/>Free to use, not forkable]
    end

    subgraph PRIVATE["PRIVATE"]
        SC[solace-cli<br/>Hub Orchestrator]
        PV[pvideo<br/>Physics Video]
        SA[solaceagi.com<br/>Hosted Platform]
    end

    PUBLIC -->|"anyone can fork"| COMMUNITY[Community Forks]
    SOURCE -->|"read + use + audit<br/>no competing products"| ENTERPRISE[Enterprise Audit]
    SOURCE -->|"converts to Apache 2.0<br/>after 4 years"| FUTURE_OSS[Future OSS]
    PRIVATE -->|"powers paid platform"| REVENUE[Revenue]

    style PUBLIC fill:#2d5016,color:#fff
    style SOURCE fill:#4a3c1e,color:#fff
    style PRIVATE fill:#3c1e1e,color:#fff
```

## Why Three Tiers?

```mermaid
graph LR
    RISK["Agentic Browser Risk"]
    RISK --> R1["Can read your email"]
    RISK --> R2["Can move your money"]
    RISK --> R3["Can sign documents"]
    RISK --> R4["Can execute code"]

    R1 --> DECISION["Safety rails must<br/>NOT be removable"]
    R2 --> DECISION
    R3 --> DECISION
    R4 --> DECISION

    DECISION --> FSL["FSL = Best of Both<br/>✅ Transparent (auditable)<br/>✅ Free (no cost)<br/>✅ Controlled (no malicious forks)<br/>✅ Time-released (→ OSS in 4 years)"]

    style RISK fill:#8b0000,color:#fff
    style FSL fill:#1a5276,color:#fff
```

## FSL Lifecycle

```mermaid
timeline
    title Solace Browser License Timeline
    2026-03-04 : FSL-1.1-Apache-2.0 released
                : Source-available, free to use
                : No competing products allowed
    2028 : Community contributions grow
         : Enterprise audits validate safety
    2030-03-04 : Change Date reached
               : Converts to Apache 2.0
               : Full open source
```

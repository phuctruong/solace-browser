# Diagram 18: App Ecosystem — Day One
**Paper:** 08-cross-app-yinyang-delight | **Auth:** 65537

## 18 Apps: Standard + No-API Exclusive + Orchestrators

```mermaid
flowchart TD
    subgraph COMMS["Communications (3)"]
        GMAIL[gmail-inbox-triage\nSafety B]
        SLACK[slack-triage\nSafety B]
        WHATSAPP[whatsapp-responder\nSafety C — No API]
    end

    subgraph PROD["Productivity (5)"]
        CAL[calendar-brief\nSafety A]
        FOCUS[focus-timer\nSafety A]
        MORNING[morning-brief\nOrchestrator]
        DRIVE[google-drive-saver\nSafety A]
        WEEKLY[weekly-digest\nOrchestrator]
    end

    subgraph SALES["Sales & Marketing (3)"]
        LINKEDIN[linkedin-outreach\nSafety C]
        YOUTUBE[youtube-script-writer\nSafety B]
        LEADS[lead-pipeline\nOrchestrator]
    end

    subgraph ENG["Engineering (2)"]
        GITHUB[github-issue-triage\nSafety B]
        REDDIT[reddit-scanner\nSafety A]
    end

    subgraph SOCIAL["Social Media (4)"]
        TWITTER_MON[twitter-monitor\nSafety A]
        TWITTER_POST[twitter-poster\nSafety C — No API]
        INSTA[instagram-poster\nSafety C — No API]
        LINKEDIN_POST[linkedin-poster\nSafety C — No API]
    end

    subgraph SHOP["Shopping (1)"]
        AMAZON[amazon-price-tracker\nSafety A — No API]
    end
```

## Orchestrator Wiring

```mermaid
flowchart TD
    subgraph MORNING_BRIEF["morning-brief (Orchestrator)"]
        direction TB
        MB_TRIGGER[06:00 daily trigger]
    end

    MB_TRIGGER --> GMAIL2[gmail-inbox-triage]
    MB_TRIGGER --> CAL2[calendar-brief]
    MB_TRIGGER --> GITHUB2[github-issue-triage]
    MB_TRIGGER --> SLACK2[slack-triage]

    GMAIL2 -->|outbox/reports/| COLLECT[Collect results]
    CAL2 -->|outbox/reports/| COLLECT
    GITHUB2 -->|outbox/reports/| COLLECT
    SLACK2 -->|outbox/reports/| COLLECT

    COLLECT --> SYNTH["LLM ONCE: synthesize all"]
    SYNTH --> REPORT["outbox/reports/morning-brief-{date}.md"]
    REPORT --> YINYANG[Surface in Yinyang]

    subgraph WEEKLY_DIGEST["weekly-digest (Orchestrator)"]
        WD_TRIGGER[Monday 08:00 trigger]
    end

    WD_TRIGGER --> MB1["morning-brief Mon"]
    WD_TRIGGER --> MB2["morning-brief Tue"]
    WD_TRIGGER --> MB3["morning-brief Wed-Fri"]
    MB1 --> WD_COLLECT[Aggregate 5 days]
    MB2 --> WD_COLLECT
    MB3 --> WD_COLLECT
    WD_COLLECT --> WD_SYNTH["LLM ONCE: weekly trends"]
    WD_SYNTH --> WD_REPORT["outbox/reports/weekly-{date}.md"]

    subgraph LEAD_PIPELINE["lead-pipeline (Orchestrator)"]
        LP_TRIGGER[On new LinkedIn connection]
    end

    LP_TRIGGER --> LI[linkedin-outreach]
    LP_TRIGGER --> GM[gmail-inbox-triage]
    LP_TRIGGER --> CA[calendar-brief]
    LI -->|lead data| LP_COLLECT[CRM-lite aggregation]
    GM -->|related emails| LP_COLLECT
    CA -->|schedule openings| LP_COLLECT
    LP_COLLECT --> LP_SYNTH["LLM ONCE: lead summary + next steps"]
```

## Cross-App Partner Map

```mermaid
flowchart LR
    GMAIL3[gmail] -->|notify| SLACK3[slack]
    GMAIL3 -->|save attachment| DRIVE3[drive]
    GMAIL3 -->|schedule follow-up| CAL3[calendar]
    GMAIL3 -->|feed summary| MORNING3[morning-brief]

    GITHUB3[github] -->|notify| SLACK3
    GITHUB3 -->|feed summary| MORNING3

    LINKEDIN3[linkedin] -->|draft reply| GMAIL3
    LINKEDIN3 -->|track lead| LEADS3[lead-pipeline]

    YOUTUBE3[youtube] -->|save script| DRIVE3
    YOUTUBE3 -->|announce| TWITTER3[twitter]

    TWITTER3 -->|feed summary| MORNING3
    REDDIT3[reddit] -->|feed summary| MORNING3
    SLACK3 -->|feed summary| MORNING3

    DRIVE3 -.->|universal save| ALL["Available to all apps"]
```

## Safety Tier Summary

```mermaid
flowchart LR
    subgraph A["Safety A — Read Only"]
        A1[calendar-brief]
        A2[focus-timer]
        A3[google-drive-saver]
        A4[twitter-monitor]
        A5[reddit-scanner]
        A6[amazon-price-tracker]
    end

    subgraph B["Safety B — Read + Draft"]
        B1[gmail-inbox-triage]
        B2[slack-triage]
        B3[github-issue-triage]
        B4[youtube-script-writer]
    end

    subgraph C["Safety C — Write + Step-Up Required"]
        C1[linkedin-outreach]
        C2[whatsapp-responder]
        C3[twitter-poster]
        C4[instagram-poster]
        C5[linkedin-poster]
    end

    A -->|no approval needed| AUTO[Standard flow]
    B -->|approval required| APPROVE[30s approval modal]
    C -->|step-up required| STEPUP["Step-up auth + 30s approval"]
```

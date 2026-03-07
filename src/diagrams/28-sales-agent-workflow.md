# Diagram 28: Sales Agent Multi-Channel Workflow
# DNA: `prospect(linkedin) → research(web) → outreach(email) → follow(cadence) → close(crm)`
# Paper: 47 (Section 21b) | Auth: 65537

```mermaid
sequenceDiagram
    participant REP as Sales Rep
    participant YY as Yinyang Sidebar
    participant LI as LinkedIn (Tab 1)
    participant WEB as Company Site (Tab 2)
    participant GM as Gmail (Tab 3)
    participant CRM as Salesforce (Tab 4)
    participant TWIN as Cloud Twin

    REP->>YY: "Find prospects matching ICP"
    YY->>LI: Search LinkedIn for title + industry + location
    LI-->>YY: Found 50 ICP matches
    YY->>REP: "50 matches. Review top 10? [Approve]"
    REP->>YY: Approve

    loop For each prospect
        YY->>LI: Visit profile, extract data
        YY->>WEB: Visit company website, extract tech stack + funding
        YY->>CRM: Check if prospect exists
        CRM-->>YY: Not in CRM
        YY->>CRM: Create lead with enriched data
        YY->>REP: "Lead created: Jane Doe, VP Eng, Series B. Send connection request? [Approve]"
        REP->>YY: Approve
        YY->>LI: Send personalized connection request
        Note over YY: Evidence: screenshot + hash chain
    end

    Note over YY,TWIN: Day 3: Cloud Twin executes follow-up cadence

    TWIN->>LI: Check connection accepted?
    alt Accepted
        TWIN->>GM: Send personalized email (recipe replay: $0.001)
        TWIN->>CRM: Update status: "email sent"
        Note over TWIN: Evidence: email content + send confirmation
    else Not Accepted
        TWIN->>LI: Send InMail (budget gate: 5 InMails/day max)
        TWIN->>CRM: Update status: "InMail sent"
    end

    TWIN-->>REP: "Morning report: 7 connections accepted, 3 emails sent, 2 replies received"
    REP->>YY: View Deal Room Evidence
    Note over YY: SHA-256 hash chain of all interactions
```

## Why This Beats Copilot for Sales
- Copilot can draft an email. Solace executes a 5-step cross-channel workflow.
- Copilot sees CRM + Outlook. Solace sees LinkedIn + email + CRM + company website + everything.
- Cloud Twin runs the follow-up cadence overnight. Rep wakes up to a report.

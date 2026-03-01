# Diagram 17: Yinyang Delight Pipeline
**Paper:** 08-cross-app-yinyang-delight | **Auth:** 65537

## Warm Token → Delight Effect

```mermaid
flowchart TD
    USER[User input] --> PHASE1["Phase 1: Small Talk Twin"]
    PHASE1 --> CPU["CPU: pattern match (~50ms)"]
    CPU --> WARM["warm_token: {mode, trigger}"]
    WARM --> LLM["LLM: validate tone (~300ms)"]
    LLM -->|confidence > 0.70| ACCEPT[Accept warm_token]
    LLM -->|confidence < 0.70| NEUTRAL[Default: neutral_professional]

    ACCEPT --> DELIGHT["YinyangDelight.respond(warmToken)"]
    DELIGHT --> EFFECT{Effect Router}
    EFFECT -->|celebrate| CONFETTI["confetti() + fanfare + toast"]
    EFFECT -->|encourage| SPARKLE["sparkles + ding + encouragement"]
    EFFECT -->|birthday| EMOJI["emoji rain 🎂🎁 + birthday tune"]
    EFFECT -->|holiday| SEASONAL["seasonal theme + greeting"]
    EFFECT -->|warm_friendly| GLOW["subtle glow + warm greeting"]
    EFFECT -->|suppress_humor| NONE["no effect — respectful silence"]
```

## Yinyang Universal Interface

```mermaid
flowchart TD
    USER[User speaks to Yinyang] --> CLASSIFY{Intent Classification}

    CLASSIFY -->|task| EXECUTE["Run app (preview → approve → execute)"]
    CLASSIFY -->|question| ANSWER["Answer from diagrams/ + docs"]
    CLASSIFY -->|customize| EDIT["Edit inbox/conventions/config.yaml"]
    CLASSIFY -->|support| EVAL{Can Yinyang fix it?}
    CLASSIFY -->|smalltalk| WARM["Warm response (jokes/facts DB)"]
    CLASSIFY -->|alert_check| ALERTS["Show pending alerts"]
    CLASSIFY -->|billing| USAGE["Show cost summary"]

    EVAL -->|yes: config change| FIX[Yinyang fixes directly]
    EVAL -->|no: needs code/new app| ESCALATE["POST /api/v1/support/ticket"]
    ESCALATE --> CONFIRM["Ticket #1234 created"]
```

## Delight Plugin Architecture

```mermaid
flowchart LR
    subgraph CORE["yinyang-delight.js (core, 8KB)"]
        CONFETTI_LIB[confetti.js]
        EMOJI_LIB[emoji.js]
        TOAST_LIB[toast.js]
        TYPING_LIB[typing.js]
        SOUND_LIB[sounds.js]
        SEASONAL_LIB[seasonal.js]
        EGGS_LIB[easter-eggs.js]
    end

    subgraph PLUGINS["User Plugins (~/.solace/yinyang/plugins/)"]
        P1[star-wars-mode.yaml]
        P2[dad-jokes.yaml]
        P3[minimal-mode.yaml]
        P4[custom-sounds.yaml]
    end

    subgraph DATA["Databases (data/default/yinyang/)"]
        JOKES[jokes.json — 50+]
        FACTS[facts.json — 50+]
        SMALL[smalltalk.json — 70+]
        HOLIDAYS[holidays.json — 12+]
        CELEBRATE[celebrations.json — 20+]
    end

    DATA --> CORE
    PLUGINS --> CORE
    CORE --> RENDER[Browser DOM effects]
```

## Alert Queue Flow

```mermaid
sequenceDiagram
    participant S as solaceagi.com
    participant Y as Yinyang
    participant U as User

    S->>S: Queue alert (new app, ticket reply, usage warning)
    U->>Y: "Hey Yinyang" (any interaction)
    Y->>S: GET /api/v1/alerts/pending
    S-->>Y: [{type: "support_reply", message: "Ticket #1234 resolved"}]
    Y->>U: "Good news — your ticket was resolved! [details]"
    U->>Y: "Thanks!"
    Y->>S: POST /api/v1/alerts/{id}/dismiss
```

## Key Moment Trigger Map

```mermaid
flowchart TD
    subgraph MOMENTS["Built-in Key Moments"]
        M1[first_run_complete]
        M2[first_app_installed]
        M3[milestone_100_runs]
        M4[streak_7_days]
        M5[birthday]
        M6[holiday_detected]
        M7[support_resolved]
        M8[budget_saved]
    end

    M1 --> E1["confetti + 'First run complete!'"]
    M2 --> E2["sparkles + 'App installed!'"]
    M3 --> E3["emoji 🏆💯 + 'Power user!'"]
    M4 --> E4["subtle glow + '7-day streak!'"]
    M5 --> E5["emoji 🎂🎁 + 'Happy birthday!'"]
    M6 --> E6["seasonal emojis + holiday greeting"]
    M7 --> E7["ding + 'Ticket resolved'"]
    M8 --> E8["sparkles + cost savings shown"]
```

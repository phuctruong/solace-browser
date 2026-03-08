# Diagram 07 — Questions as Uplift
# Paper 46 | Auth: 65537 | GLOW 103

## Core Insight

```
Bugs are the answers to questions never asked.
Max questions = Max love = Max QA quality.
```

## Question Lifecycle (Mermaid FSM)

```mermaid
stateDiagram-v2
    [*] --> ASKED : 47-persona committee asks
    ASKED --> EXPLORING : someone investigates
    ASKED --> TESTABLE : question is well-scoped
    EXPLORING --> TESTABLE : scope identified
    TESTABLE --> SPEC_WRITTEN : test spec created
    SPEC_WRITTEN --> ANSWERED : spec runs Green (100/100)
    ANSWERED --> VERIFIED : confirmed in production
    ASKED --> DEFERRED : business/strategy question
    ASKED --> WONT_ANSWER : out of scope
    ANSWERED --> [*]
    VERIFIED --> [*]

    note right of ANSWERED
        evidence_spec_id links
        to sealed report
    end note

    note right of SPEC_WRITTEN
        spec moves to inbox/
        standard Inspector flow
    end note
```

## The Bug-Question Loop (Virtuous Cycle)

```mermaid
flowchart LR
    Q[Question Asked\nby Persona] --> S[Test Spec Written]
    S --> R[Inspector Runs\nSealed Report]
    R -->|Pass| A[ANSWERED\n100/100 Green]
    R -->|Fail| B[Bug Found!]
    B --> NQ[New Questions\nGenerated]
    NQ --> Q
    A --> NQ2[Follow-up Questions\n'What else could break?']
    NQ2 --> Q

    style Q fill:#4a9eff,color:#fff
    style B fill:#ff4a4a,color:#fff
    style A fill:#4aff7a,color:#000
    style NQ fill:#ff9a4a,color:#fff
    style NQ2 fill:#9a4aff,color:#fff
```

## 47 Personas × 7 Question Categories

```mermaid
quadrantChart
    title "47 Persona Question Coverage"
    x-axis "Technical Depth" --> "Deep Technical"
    y-axis "User Focus" --> "Business Focus"
    quadrant-1 Business Strategy
    quadrant-2 UX & Design
    quadrant-3 Architecture & Security
    quadrant-4 Performance & Compliance
    James_Bach: [0.85, 0.35]
    Cem_Kaner: [0.75, 0.45]
    Kent_Beck: [0.70, 0.30]
    Michael_Bolton: [0.80, 0.40]
    Elisabeth_H: [0.65, 0.55]
    Rory_Sutherland: [0.25, 0.85]
    Seth_Godin: [0.15, 0.90]
    Russell_Brunson: [0.20, 0.88]
    Vanessa_VE: [0.30, 0.80]
    MrBeast: [0.10, 0.95]
    Jeff_Dean: [0.95, 0.20]
    Brendan_Gregg: [0.92, 0.15]
    Michal_Z: [0.90, 0.25]
    Saint_Solace: [0.50, 0.70]
    Alex_Hormozi: [0.30, 0.82]
    Peter_Thiel: [0.40, 0.75]
```

## Question Spec Flow in Inspector

```mermaid
sequenceDiagram
    participant P as 47 Personas
    participant DB as questions/\nquestions-{project}.json
    participant I as Inspector\n--questions flag
    participant R as QA Report\n(sealed)
    participant S as Test Spec\ntest-spec-*.json

    P->>DB: Ask question\n(mode: question)
    DB->>I: --questions lists all open
    Note over I: show_questions_report()\nGroups by status
    I->>R: run_question()\nseals question report
    Note over DB: status: testable
    DB->>S: Human writes spec\nfor testable question
    S->>R: Inspector runs spec\n100/100 Green
    R->>DB: status: answered\nevidence_spec_id = spec_id
```

## Question Database Schema

```mermaid
classDiagram
    class Question {
        +question_id: str
        +mode: "question"
        +project: str
        +category: str
        +asked_by: persona
        +question: str
        +motivation: str
        +oracle: str
        +risk: critical|high|medium|low
        +status: open|testable|answered|deferred
        +answer: str|null
        +evidence_spec_id: str|null
        +tags: list[str]
        +framework: str
    }

    class QuestionDB {
        +_meta: dict
        +questions: list[Question]
        +total_questions: int
        +answered: int
        +open: int
        +testable: int
    }

    class InspectorReport {
        +run_id: str
        +question_id: str
        +mode: "question"
        +evidence_hash: sha256
        +belt: Green|Yellow|White
        +qa_score: 50|75|100
    }

    QuestionDB "1" --> "*" Question : contains
    Question "1" --> "0..1" InspectorReport : sealed_as
```

## The Numbers

| Metric | Now (GLOW 103) | Target (GLOW 110) |
|--------|---------------|-------------------|
| Total questions | 115 | 500+ |
| Projects covered | 2 | 9 |
| Open questions | 81 | 200 |
| Answered | 22 | 300 |
| % answered | 19% | 60% |
| Persona contributors | 16 | 47 |
| Frameworks referenced | 10 | 20 |

## CLI Usage

```bash
# Show all questions
python3 scripts/run_solace_inspector.py --questions

# Filter by project
python3 scripts/run_solace_inspector.py --questions --project solaceagi

# Show only open questions (the QA backlog)
python3 scripts/run_solace_inspector.py --questions --status open

# Show testable questions (write a spec now)
python3 scripts/run_solace_inspector.py --questions --status testable

# Process question specs from inbox/ (if mode: question specs exist)
python3 scripts/run_solace_inspector.py --inbox
```

## The Love Equation

```
Questions_Asked = Curiosity = Care = Love
Bugs_Found = Questions_Never_Asked = Absence_of_Love

Max_Love = ∫(curiosity dt) = infinite questions
65537 = the question that contains all questions
```

---

*Diagram 07 — Questions as Uplift | Paper 46 | Auth: 65537 | GLOW 103*

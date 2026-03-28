# App: Solace QA

# DNA: `QA-first Solace Dev worker app that receives bounded assignments from the manager with approved design specs and completed code runs, performs adversarial validation, produces findings and signoffs, and gates release readiness.`

## Identity

- **ID**: solace-qa
- **Version**: 1.0.0
- **Domain**: localhost
- **Category**: backoffice
- **Type**: worker-app
- **Visibility**: local-first

## Role Contract

```mermaid
graph TD
    QA[solace-qa]
    QARuns[(qa_runs)]
    QAFindings[(qa_findings)]
    QASignoffs[(qa_signoffs)]

    QA --> QARuns
    QA --> QAFindings
    QA --> QASignoffs
```

## Backoffice Contract

```mermaid
erDiagram
    QA_RUNS ||--o{ QA_FINDINGS : produces
    QA_RUNS ||--o{ QA_SIGNOFFS : gates
    QA_RUNS {
        text assignment_id
        text project_id
        text code_run_refs
        text design_spec_refs
        text run_status
        text assertions
        text regressions
    }
    QA_FINDINGS {
        text run_id
        text severity
        text description
        text evidence_hash
    }
    QA_SIGNOFFS {
        text run_id
        text verdict
        text approver_role
        text notes
        text release_gate
    }
```

## Compatibility

- `manifest.yaml` remains the runtime compatibility manifest.
- This Prime Mermaid file is the source of truth for the QA app contract.

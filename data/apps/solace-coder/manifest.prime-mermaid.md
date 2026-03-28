# App: Solace Coder

# DNA: `Coder-first Solace Dev worker app that receives bounded assignments from the manager with approved design artifacts, implements code changes, produces diff summaries and test evidence, and emits implementation artifacts back to the manager pipeline.`

## Identity

- **ID**: solace-coder
- **Version**: 1.0.0
- **Domain**: localhost
- **Category**: backoffice
- **Type**: worker-app
- **Visibility**: local-first

## Role Contract

```mermaid
graph TD
    Coder[solace-coder]
    CodeRuns[(code_runs)]
    CodeArtifacts[(code_artifacts)]
    CoderReviews[(coder_reviews)]

    Coder --> CodeRuns
    Coder --> CodeArtifacts
    Coder --> CoderReviews
```

## Backoffice Contract

```mermaid
erDiagram
    CODE_RUNS ||--o{ CODE_ARTIFACTS : produces
    CODE_RUNS ||--o{ CODER_REVIEWS : requires
    CODE_RUNS {
        text assignment_id
        text project_id
        text target_files
        text design_spec_refs
        text run_status
        text diff_summary
        text test_output
    }
    CODE_ARTIFACTS {
        text run_id
        text file_path
        text change_type
        text evidence_hash
    }
    CODER_REVIEWS {
        text run_id
        text reviewer_role
        text verdict
        text notes
    }
```

## Compatibility

- `manifest.yaml` remains the runtime compatibility manifest.
- This Prime Mermaid file is the source of truth for the coder app contract.

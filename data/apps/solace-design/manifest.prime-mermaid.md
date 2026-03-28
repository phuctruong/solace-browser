# App: Solace Design

# DNA: `Design-first Solace Dev worker app that receives bounded assignments from the manager, produces page/state/component design specs, and emits review artifacts back to the manager pipeline.`

## Identity

- **ID**: solace-design
- **Version**: 1.0.0
- **Domain**: localhost
- **Category**: backoffice
- **Type**: worker-app
- **Visibility**: local-first

## Role Contract

```mermaid
graph TD
    Design[solace-design]
    DesignSpecs[(design_specs)]
    DesignReviews[(design_reviews)]

    Design --> DesignSpecs
    Design --> DesignReviews
```

## Backoffice Contract

```mermaid
erDiagram
    DESIGN_SPECS ||--o{ DESIGN_REVIEWS : requires
    DESIGN_SPECS {
        text assignment_id
        text project_id
        text page_scope
        text state_scope
        text spec_type
        text content
        text status
    }
    DESIGN_REVIEWS {
        text spec_id
        text reviewer_role
        text verdict
        text notes
    }
```

## Compatibility

- `manifest.yaml` remains the runtime compatibility manifest.
- This Prime Mermaid file is the source of truth for the design app contract.

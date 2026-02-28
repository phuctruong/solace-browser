# TASK-001 Recipe Hardening

## Goal

Prove deterministic recipe parsing and replay behavior across the mixed recipe corpus.

## Flow

```mermaid
stateDiagram-v2
    [*] --> LoadArtifact
    LoadArtifact --> ParseJsonRecipe: .json
    LoadArtifact --> ParseMarkdownRecipe: .md
    LoadArtifact --> RejectArtifact: empty/unknown

    ParseJsonRecipe --> NormalizeRecipe
    ParseMarkdownRecipe --> NormalizeRecipe

    NormalizeRecipe --> ValidateRequiredFields
    ValidateRequiredFields --> BuildDeterministicDag
    BuildDeterministicDag --> HashCanonicalDag
    HashCanonicalDag --> CacheLookup

    CacheLookup --> ExecuteRecipe: cache miss
    CacheLookup --> ReplaySealedOutput: cache hit / replay request

    ExecuteRecipe --> SealOutput
    SealOutput --> VerifyReplayHash
    ReplaySealedOutput --> VerifyReplayHash

    VerifyReplayHash --> Success: hash matches
    VerifyReplayHash --> RejectArtifact: hash mismatch
    RejectArtifact --> [*]
    Success --> [*]
```

## Notes

- Parsing must be stable under whitespace-only changes.
- JSON recipes normalize multiple legacy shapes into one deterministic DAG view.
- Replay never calls the browser or an LLM; it compares canonical sealed artifacts only.
- Invalid JSON, missing fields, empty files, unknown actions, and circular DAGs must raise typed errors.

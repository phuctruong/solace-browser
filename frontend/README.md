# Solace Browser Frontend (Phase 4.1)

React + TypeScript frontend workspace for the Solace Browser Phase 4.1 flow.

## Implemented

- Forced sign-up entry from locked `/home`
- Popup auth handshake stub + encrypted API key vault payload
- LLM setup + membership unlock flow
- App grid + runs table + app/run detail routes
- Approval modal required before run execution
- Deterministic headless execution stub + evidence/hash chain wiring
- Cost savings widget and hash verification display

## Run

```bash
cd frontend
npm install
npm test
npm run build
npm run dev
```

## Evidence

Phase 4.1 evidence artifacts:

- `scratch/evidence/phase_4_1/test_results.json`
- `scratch/evidence/phase_4_1/deterministic_replay_proof.json`
- `scratch/evidence/phase_4_1/approval_hash_chain_proof.json`
- `scratch/evidence/phase_4_1/approval_hash_chain_proof.jsonl`
- `scratch/evidence/phase_4_1/ui_workflow_proof.json`

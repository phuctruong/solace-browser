<!-- Diagram: project-map -->
# Solace Browser — Project Map
# DNA: `project = runtime(rust,27K) + hub(tauri,UI) + data(40_apps) + diagrams(50) + chromium(fork)`
# Auth: 65537 | State: GOOD | Version: 1.0.0

## Directory Map

```mermaid
graph TD
    ROOT["solace-browser/"]
    
    subgraph PRODUCT["Product Code (diagrammed)"]
        RUNTIME["solace-runtime/src/<br>77 Rust files, 27,710 lines<br>DIAGRAMS: specs/diagrams/hub/*"]
        HUB_UI["solace-hub/src/<br>Hub UI (JS/HTML/CSS)<br>DIAGRAMS: hub-ux-architecture, hub-dashboard*"]
        DATA["data/apps/<br>40 app manifests<br>DIAGRAMS: hub-runtime (ENGINE nodes)"]
    end

    subgraph SPECS["Specification Layer"]
        DIAG_HUB["specs/diagrams/hub/<br>46 PM diagrams"]
        DIAG_BROWSER["specs/diagrams/browser/<br>4 PM diagrams"]
    end

    subgraph BUILD["Build & Infrastructure"]
        CARGO["Cargo.toml + Cargo.lock<br>Rust dependencies"]
        CHROMIUM["source/<br>Chromium fork (upstream)<br>DIAGRAM: browser-chromium-build"]
        DEPOT["depot_tools/<br>Google build tooling"]
        TARGET["target/<br>Rust build cache (gitignored)"]
    end

    subgraph SUPPORT_CODE["Supporting Code"]
        WEB["web/<br>Static web assets (495 files)"]
        SCRIPTS["scripts/<br>Dev/build scripts (140 files)"]
        TESTS["tests/<br>Integration tests (630 files)"]
        APPS["apps/<br>App templates (51 files)"]
        SRC["src/<br>C++ browser source (65 files)"]
        SNAP["snap/<br>Linux package config"]
        RESOURCES["resources/<br>Icons/assets"]
    end

    subgraph LEGACY["Legacy (should migrate to Rust)"]
        YIN_PY["yinyang_server.py<br>Python MCP bridge"]
        YIN_MCP["yinyang_mcp_server.py<br>Python MCP server"]
        HUB_TUNNEL["hub_tunnel_client.py<br>Python tunnel client"]
        SOLACE_CLI["solace_cli.py<br>Python CLI"]
        EVIDENCE_PY["evidence_bundle.py<br>Python evidence tool"]
    end

    subgraph SCRATCH["scratch/ (gitignored — noise quarantine)"]
        CLEANUP["_cleanup_2026-03-29/<br>dist, archive, pycache, aider, patches"]
    end

    ROOT --> PRODUCT
    ROOT --> SPECS
    ROOT --> BUILD
    ROOT --> SUPPORT_CODE
    ROOT --> LEGACY
    ROOT --> SCRATCH

    classDef diagrammed fill:#e8f5e9,stroke:#2e7d32
    classDef build fill:#e3f2fd,stroke:#1565c0
    classDef legacy fill:#fff9c4,stroke:#f9a825
    classDef scratch fill:#ffefef,stroke:#cc0000

    class RUNTIME,HUB_UI,DATA diagrammed
    class CARGO,CHROMIUM,DEPOT,TARGET build
    class YIN_PY,YIN_MCP,HUB_TUNNEL,SOLACE_CLI,EVIDENCE_PY legacy
    class CLEANUP scratch
```

## Coverage Rule
Every file outside `scratch/`, `target/`, `source/`, `depot_tools/`, and `.git/`
MUST be referenced by at least one PM diagram's `## Covered Files` section.

## File → Diagram Index

| Path | Diagram |
|------|---------|
| `solace-runtime/src/main.rs` | hub-runtime |
| `solace-runtime/src/server.rs` | hub-runtime |
| `solace-runtime/src/state.rs` | hub-runtime |
| `solace-runtime/src/routes/*.rs` (38 files) | hub-runtime + specific feature diagrams |
| `solace-runtime/src/app_engine/*.rs` | hub-runtime, hub-llm-routing, hub-cross-app |
| `solace-runtime/src/backoffice/*.rs` | hub-cloud-backoffice, hub-runtime |
| `solace-runtime/src/pzip/*.rs` | hub-evidence |
| `solace-runtime/src/auth/*.rs` | hub-runtime |
| `solace-runtime/src/mcp.rs` | hub-mcp |
| `solace-runtime/src/cron.rs` | hub-cron |
| `solace-runtime/src/cloud.rs` | hub-runtime |
| `solace-runtime/src/crypto.rs` | hub-runtime |
| `solace-runtime/src/persistence.rs` | hub-runtime |
| `solace-runtime/src/evidence.rs` | hub-evidence |
| `solace-runtime/src/event_log.rs` | hub-app-event-log |
| `solace-runtime/src/updates.rs` | hub-runtime |
| `solace-hub/src/*` | hub-ux-architecture, hub-dashboard |
| `data/apps/` | hub-runtime |
| `yinyang_server.py` | hub-runtime (LEGACY) |
| `web/` | hub-ux-architecture |
| `scripts/` | browser-chromium-build |
| `tests/` | Referenced in diagram Verification sections |
| `.gitignore` | project-map |
| `apps/README.md` | hub-domain-ecosystem |
| `Dockerfile.cloud-twin` | hub-deployment-pipeline |
| `cloudbuild-twin.yaml` | hub-deployment-pipeline |

### Top-Level Config & Documentation
| File | Purpose |
|------|---------|
| `Cargo.toml` | Rust manifest — defines solace-runtime crate |
| `Makefile` | Build automation — `make build`, `make test` |
| `README.md` | Project documentation |
| `ROADMAP.md` | Product roadmap (1,379 lines) |
| `TODO.md` | Active task list |
| `NORTHSTAR.md` | Project vision / north star |
| `CHANGELOG.md` | Version history |
| `CONTRIBUTING.md` | Contribution guidelines |
| `SECURITY.md` | Security policy |
| `CLAUDE.md` | AI coding agent instructions |
| `GEMINI.md` | AI coding agent instructions |
| `cloudbuild.yaml` | GCP Cloud Build main config |
| `cloudbuild-prod.yaml` | GCP Cloud Build production |
| `cloudbuild-browser.yaml` | GCP Cloud Build browser |
| `docker-compose.yml` | Docker orchestration |
| `docker-compose.dev.yml` | Docker dev environment |
| `requirements.txt` | Python dependencies |
| `requirements-lock.txt` | Python dependency lock |
| `pyproject.toml` | Python project config |
| `pytest.ini` | Python test config |
| `ruff.toml` | Python linter config |
| `load_env.sh` | Environment variable loader |
| `sbom.json` | Software Bill of Materials |

## Covered Files
```
docs:
  - solace-browser/README.md
  - solace-browser/ROADMAP.md
  - solace-browser/TODO.md
  - solace-browser/NORTHSTAR.md
  - solace-browser/CHANGELOG.md
  - solace-browser/CONTRIBUTING.md
  - solace-browser/SECURITY.md
  - solace-browser/CLAUDE.md
  - solace-browser/GEMINI.md
config:
  - solace-browser/.gitignore
  - solace-browser/Cargo.toml
  - solace-browser/Makefile
  - solace-browser/cloudbuild.yaml
  - solace-browser/cloudbuild-prod.yaml
  - solace-browser/cloudbuild-browser.yaml
  - solace-browser/docker-compose.yml
  - solace-browser/docker-compose.dev.yml
  - solace-browser/requirements.txt
  - solace-browser/requirements-lock.txt
  - solace-browser/pyproject.toml
  - solace-browser/pytest.ini
  - solace-browser/ruff.toml
  - solace-browser/load_env.sh
  - solace-browser/sbom.json
```

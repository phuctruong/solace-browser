# Diagram: SolaceBrowser Full Stack

**ID:** solace-browser-full-stack
**Version:** 1.0.0
**Type:** Architecture diagram (full system)
**Primary Axiom:** NORTHSTAR (Universal Portal)
**Tags:** architecture, full-stack, local, cloud, solaceagi, oauth3, recipes, evidence, twin, machine

---

## Purpose

The full-stack diagram shows the complete SolaceBrowser system from the user's intent to the cloud, including all 5 control surfaces, the local browser layers, the cloud twin, the 3-layer access model (web + machine + tunnel), and the integration with solaceagi.com.

---

## Diagram: Complete System View

```mermaid
flowchart TB
    subgraph USER_FACING["5 Control Surfaces"]
        CS1["AI Agent\n(Claude Code + stillwater skills)"]
        CS2["CLI\n(solace-cli browser run)"]
        CS3["OAuth3 Web\n(solaceagi.com dashboard)"]
        CS4["Native Tunnel\n(built-in reverse proxy)"]
        CS5["Download\n(Tauri/Electron app)"]
    end

    subgraph LOCAL_BROWSER["Local Browser (localhost:9222)"]
        direction TB

        subgraph WEB_LAYER["Web Layer (OAuth3-gated)"]
            WL1["Recipe Engine\n(cache + replay)"]
            WL2["OAuth3 Gate\n(4-gate cascade)"]
            WL3["Snapshot Engine\n(Playwright, ARIA refs)"]
            WL4["Anti-Detection\n(Bezier, fingerprint)"]
        end

        subgraph MACHINE_LAYER["Machine Layer (OAuth3-gated)"]
            ML1["File Access\n(13 scopes, path traversal blocked)"]
            ML2["Terminal\n(allowlist only, no BLOCKED_COMMANDS)"]
            ML3["System State\n(read-only sensors)"]
        end

        subgraph TUNNEL_LAYER["Tunnel Layer"]
            TL1["Built-in reverse proxy\n(wss://, cert-pinned)"]
            TL2["Step-up required\nfor tunnel access"]
        end

        subgraph EVIDENCE_LAYER["Evidence Layer"]
            EV1["PZip snapshots\n~/.solace/evidence/"]
            EV2["SHA256 chain\n(tamper-evident)"]
            EV3["ALCOA+ bundles\n(Part 11 compliant)"]
        end
    end

    subgraph CLOUD["Cloud Twin (solaceagi.com)"]
        direction TB
        CT1["Headless browser\n(same session as local)"]
        CT2["Recipe replay\n(haiku, 24/7)"]
        CT3["Task queue\n(Kanban view)"]
        CT4["Evidence sync\n(encrypted)"]
        CT5["LLM Proxy\n(Together.ai / OpenRouter)"]
    end

    subgraph GOVERNANCE["Governance Layer"]
        GV1["stillwater verification\n(rung system)"]
        GV2["solace-cli\n(CLI auth + OAuth3 vault)"]
        GV3["Stillwater Store\n(skill governance)"]
    end

    USER_FACING --> LOCAL_BROWSER
    TL1 <-->|"AES-256-GCM sync\nzero-knowledge"| CLOUD
    LOCAL_BROWSER <--> GOVERNANCE
    CLOUD <--> GOVERNANCE
```

---

## Diagram: 3-Layer Access Model

```mermaid
flowchart LR
    subgraph ACCESS["3 Access Layers"]
        direction TB

        subgraph WEB["Web Layer"]
            W1["LinkedIn, Gmail, Twitter"]
            W2["Reddit, HackerNews, GitHub"]
            W3["10+ platforms via recipes"]
            W4["OAuth3 scope: platform.action"]
        end

        subgraph MACHINE["Machine Layer"]
            M1["File read/write\n(scope: machine.read_file, machine.write_file)"]
            M2["Terminal execute\n(scope: machine.execute_command)"]
            M3["System sensors\n(scope: machine.system_info)"]
            M4["Path traversal: BLOCKED\n(../.. always rejected)"]
        end

        subgraph TUNNEL["Tunnel Layer"]
            T1["Remote control from solaceagi.com"]
            T2["wss:// only (no ws://)"]
            T3["Step-up required\n(scope: tunnel.connect)"]
            T4["Bandwidth tracked"]
        end
    end

    OAUTH3["OAuth3 Gate\n(enforces all 3 layers)"]
    OAUTH3 --> WEB
    OAUTH3 --> MACHINE
    OAUTH3 --> TUNNEL
```

---

## Diagram: Integration with Phuc Ecosystem

```mermaid
flowchart TD
    SB["solace-browser\n(this project, OSS)"]

    SC["solace-cli\n(PRIVATE)\nextends stillwater/cli\nOAuth3 vault mgmt"]

    SW["stillwater\n(OSS)\nverification + skills\nrung system"]

    SG["solaceagi.com\n(PAID)\nhosted platform\ncloud twin"]

    PAUDIO["paudio\n(OSS)\ndeterministic TTS/STT\nVoice Arena"]

    PVIDEO["pvideo\n(PRIVATE)\nIF Theory video/avatar\nSecret sauce"]

    AVATAR["AI Avatar\nsolaceagi.com\npaudio voice + pvideo face\n+ stillwater verification"]

    SB <-->|OAuth3 reference impl| SC
    SB <-->|rung verification| SW
    SB <-->|cloud twin backend| SG
    SG <-->|voice| PAUDIO
    SG <-->|visual| PVIDEO
    PAUDIO & PVIDEO --> AVATAR
    SW --> AVATAR
```

---

## Diagram: Skill Stack (Full)

```mermaid
classDiagram
    class BrowserSession {
        +browser_snapshot
        +browser_recipe_engine
        +browser_oauth3_gate
        +browser_evidence
        +browser_anti_detect
        +browser_twin_sync
    }

    class PrimeSafety {
        +authority_chain
        +network_default_off
        +write_default_repo_only
        +stop_conditions
    }

    class SwarmAgents {
        +recipe_builder
        +selector_healer
        +oauth3_auditor
        +evidence_reviewer
        +coder
        +skeptic
        +planner
    }

    class Recipes {
        +browser_snapshot_audit
        +oauth3_consent_flow
        +twin_sync
        +recipe_builder
        +selector_heal
        +evidence_review
        +linkedin_create_post
        +gmail_send_email
        +hackernews_upvote
    }

    BrowserSession --> PrimeSafety : governed by
    BrowserSession --> SwarmAgents : dispatches to
    SwarmAgents --> Recipes : executes
```

---

## Diagram: Belt Progression + Feature Unlock

```mermaid
flowchart TD
    WHITE["White Belt (Free)\n$0\n• All UI\n• Local recipes (LinkedIn/Gmail)\n• BYOK\n• 100 snapshots, 7-day history"]
    YELLOW["Yellow Belt (Student)\n$8/mo\n• Managed LLM (no API key)\n• 30-day evidence\n• 20 OAuth3 tokens\n• 1,000 snapshots"]
    ORANGE["Orange Belt (Warrior)\n$48/mo\n• Cloud twin 24/7\n• OAuth3 vault\n• 90-day evidence\n• rung 65537\n• 10,000 snapshots"]
    GREEN["Green Belt (Master)\n$88/user/mo\n• Team tokens\n• SOC2 audit\n• Private Stillwater Store\n• SAML SSO\n• Unlimited snapshots, 1yr"]
    BLACK["Black Belt (Grandmaster)\n$188+/mo\n• Dedicated nodes\n• On-prem\n• Custom governance\n• Unlimited forever"]

    WHITE --> YELLOW --> ORANGE --> GREEN --> BLACK
```

---

## Diagram: Data Flow (Credential Security)

```mermaid
flowchart LR
    USER_CREDS["User Credentials\n(passwords, cookies)"]

    subgraph LOCAL_ONLY["Stays on local machine ONLY"]
        VAULT["~/.solace/vault/\n(AES-256-GCM, user key)"]
        MASTER_KEY["User master key\n(derived from password)"]
    end

    subgraph WIRE["Wire (wss://)"]
        ENC["Encrypted ciphertext\nonly"]
    end

    subgraph CLOUD_RECV["Cloud receives"]
        CIPHERTEXT["Ciphertext\n(cannot decrypt\nwithout user key)"]
    end

    USER_CREDS --> VAULT
    VAULT -->|"Encrypted\n(user key)"| ENC --> CIPHERTEXT

    NEVER["NEVER transmitted:\n• Plaintext cookies\n• Passwords\n• User master key\n• Vault contents unencrypted"]
    VAULT --- NEVER
```

---

## Notes

### Why This Stack Wins

The full stack is designed around one principle: the user's data is theirs, and AI agents operate as their authorized delegates — not as independent actors with their own credentials.

Seven structural moats (all competitors have 0–2):
1. Recipe system → 70% cache hit → 3x cheaper COGS
2. PrimeWiki → domain-aware navigation
3. Twin architecture → local + cloud delegation
4. Anti-detection → human-like browser behavior
5. Stillwater verification → evidence bundle per task
6. OAuth3 protocol → scoped consent, revocation, audit trail
7. Machine layer → OAuth3-gated file/terminal access

### The Canonical OSS Reference

`solace-browser` is the reference implementation of the OAuth3 open standard. Anyone who wants to verify what OAuth3 compliance looks like in a browser automation context can read this codebase.

`solace-cli` (private) extends this with vault management. `solaceagi.com` extends it further with cloud execution and managed LLM. The OSS core ensures the standard is open; the extensions are where the business model lives.

---

## Related Artifacts

- `NORTHSTAR.md` — full NORTHSTAR vision document
- `ROADMAP.md` — phase-by-phase build plan
- `data/default/diagrams/browser-multi-layer-architecture.md` — 5-layer architecture detail
- `data/default/diagrams/oauth3-enforcement-flow.md` — OAuth3 gate detail
- `data/default/diagrams/twin-sync-flow.md` — twin sync detail
- `data/default/diagrams/evidence-pipeline.md` — evidence pipeline detail

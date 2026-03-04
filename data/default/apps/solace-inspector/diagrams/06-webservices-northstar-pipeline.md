# Diagram 06: Webservices-First Northstar Pipeline
# Solace Inspector | Auth: 65537 | GLOW: L | Updated: 2026-03-03
# Paper 43 | DNA: inspector(northstar) = certify(cpu) * abcd(llm) * reverse(frontend)

## The Full Pipeline (SW5.0 Northstar Edition)

```mermaid
flowchart TD
    subgraph Contracts["📋 NORTHSTAR CONTRACTS (inbox/northstars/)"]
        N1["northstar-api-llm-chat.json\nmethod: POST\nendpoint: /api/v1/llm/chat\nguarantees: [auth, cost_usd, latency<30s]"]
        N2["northstar-api-health.json\nmethod: GET\nendpoint: /api/v1/health\nguarantees: [always 200, {status:ok}]"]
        N3["northstar-api-auth.json\nmethod: POST\nendpoint: /api/v1/auth\nguarantees: [401 no token, 200 valid]"]
    end

    subgraph CPUCert["⚙️ CPU CERTIFICATION (deterministic)"]
        C1["CLI spec: curl -s /health\nstdout_contains: [ok]\nexit_code: 0"]
        C2["CLI spec: curl -s /auth (no token)\nstdout_contains: [401]\nexit_code: 0"]
        C3["CLI spec: curl -s /version\nstdout_contains: [version, sha]"]
        CPU_SEAL["SHA-256 Seal\nstatus: CPU_CERTIFIED\n$0.00 cost"]
    end

    subgraph ABCDCert["🔬 ABCD CERTIFICATION (LLM nodes)"]
        A["Model A: Llama-70B\n$0.59/1M tokens\nTogether.ai"]
        B["Model B: Mixtral-8x22B\n$1.20/1M tokens\nOpenRouter"]
        C["Model C: Claude Sonnet\n$3.00/1M tokens\nOpenRouter"]
        D["Model D: GPT-4o\n$5.00/1M tokens\nOpenRouter"]
        WINNER["🏆 Winner: cheapest passing\nEvidence: cost delta sealed\nRouting table: ABCD_CERTIFIED"]
    end

    subgraph Frontend["🖥️ FRONTEND (reverse-engineered)"]
        F1["web/settings.html\nAsk YinYang → uses sealed\n/api/yinyang/chat route"]
        F2["web/home.html\nYinYang greeting → uses sealed\n/api/v1/llm/chat route"]
        F3["web/app-store.html\nModel picker → displays\nsealed ABCD winner"]
    end

    subgraph WebQA["🔍 WEB QA (heuristics only)"]
        W1["Inspector web mode\nPlaywright → ARIA → DOM\nHeuristics → Score"]
        W2["100/100 Green\nFrontend sealed\nFull chain complete"]
    end

    N1 --> CPUCert
    N2 --> CPUCert
    N3 --> CPUCert
    N1 --> ABCDCert

    C1 --> CPU_SEAL
    C2 --> CPU_SEAL
    C3 --> CPU_SEAL

    A --> WINNER
    B --> WINNER
    C --> WINNER
    D --> WINNER

    CPU_SEAL --> Frontend
    WINNER --> Frontend

    F1 --> WebQA
    F2 --> WebQA
    F3 --> WebQA

    W1 --> W2

    style Contracts fill:#1a1a2e,stroke:#4ecdc4,color:#fff
    style CPUCert fill:#1a2e1a,stroke:#52b788,color:#fff
    style ABCDCert fill:#2e1a00,stroke:#ffa726,color:#fff
    style Frontend fill:#1a1a2e,stroke:#7c4dff,color:#fff
    style WebQA fill:#1a472a,stroke:#52b788,color:#fff
    style WINNER fill:#1a2e00,stroke:#76ff03,color:#fff
```

## CPU vs ABCD Decision Matrix

```mermaid
flowchart LR
    E([Endpoint to certify]) --> Q{Has LLM\nin the path?}
    Q -->|No — deterministic| CPU[CPU Certification\ncurl -s → assert → seal\nCost: $0.00\nStatus: CPU_CERTIFIED]
    Q -->|Yes — probabilistic| ABCD[ABCD Certification\nA→B→C→D → find winner → seal\nCost: ~$0.01 test run\nStatus: ABCD_CERTIFIED]

    CPU --> DONE[✅ Frontend can depend\non this endpoint\nSHA-256 sealed]
    ABCD --> DONE

    CPU -.->|Re-certify when?| R1[Contract changes\nor server updates]
    ABCD -.->|Re-certify when?| R2[Model prices change\nor quality drifts]
```

## ABCD Test Results (Evidence Format)

```
Run ID: abcd-20260303-150000-abc123
Endpoint: POST /api/v1/llm/chat
Prompt: "What is 2+2? Answer in one word."
Quality threshold: stdout_contains ["four"] (case-insensitive)

Model  | Response   | Latency | Cost/1M | Pass? | Notes
───────────────────────────────────────────────────────────────
A      | "Four"     | 0.82s   | $0.59   | ✅    | Llama-3.3-70B
B      | "Four"     | 1.15s   | $1.20   | ✅    | Mixtral-8x22B
C      | "Four"     | 0.91s   | $3.00   | ✅    | Claude Sonnet
D      | "Four"     | 1.08s   | $5.00   | ✅    | GPT-4o

🏆 Winner: A (Llama-3.3-70B)
   Reason: cheapest model that passes quality threshold
   Cost delta vs D: 88% savings ($0.59 vs $5.00)
   Routing recommendation: use A for factual/simple task class

Evidence sealed: sha256:abc123...
Status: ABCD_CERTIFIED
```

## The Solaceagi.com Claim — Proved

```
Claim on website:
  "We manage your LLM calls and get you the best deal."

Proof via Inspector ABCD:
  Every LLM endpoint → ABCD test → cheapest passing model → sealed
  Routing table = ABCD results = evidence
  "Best deal" = not marketing. It's a sealed SHA-256 report.

This is the ONLY way to make "best deal" claim truthful:
  ✅ Run the test (ABCD mode)
  ✅ Seal the result (SHA-256)
  ✅ Route using evidence (ABCD winner)
  ✅ Re-test when prices change (quarterly ABCD refresh)
```

## Northstar Certification States

```
UNCERTIFIED        → contract exists, no tests run yet
CPU_CERTIFIED      → deterministic path verified + sealed
ABCD_CERTIFIED     → LLM path verified + cheapest model found + sealed
FULL_CERTIFIED     → CPU + ABCD + Frontend web-mode all Green
STALE              → certified > 90 days ago (re-test recommended)
BROKEN             → last certification failed (blocker — fix before deploy)
```

## The Frontend Reverse Engineering Rule

```
❌ WRONG:
   UI dev: "I think the API returns {cost_usd}... let me guess."
   → builds UI with fake/assumed data
   → finds out API is different in staging
   → 2 weeks of misalignment

✅ CORRECT:
   Inspector certifies: POST /api/v1/llm/chat → {content, model, usage, cost_usd} ✅
   UI dev: "The certified contract says cost_usd exists. I'll display it."
   → builds against sealed reality
   → web-mode inspector verifies the display
   → zero misalignment
```

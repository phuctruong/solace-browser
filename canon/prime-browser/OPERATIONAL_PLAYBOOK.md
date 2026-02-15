# 📖 Prime Browser: Operational Playbook

> **Version:** 1.0.0
> **Status:** 🎮 ACTIVE
> **Target:** Solace Browser Execution Loop

---

## 1. THE EXECUTION LOOP (DREAM-ACT-VERIFY)

To run a successful browser operation, follow the 4-step cycle:

### Step 1: Record (Dream)
*   **Action:** Manually record the high-value interaction using the Solace Browser extension.
*   **Result:** `episode.jsonl` containing raw snapshots and actions.
*   **Check:** Verify snapshots are canonicalized via Phase 5 logic.

### Step 2: Compile (Decide)
*   **Action:** Use the `RefMapBuilder` (Phase 3) to generate stable selectors.
*   **Result:** `recipe.pm.yaml` (Prime Mermaid DAG).
*   **Check:** Run the **RTC (Round-Trip Canonicalization)** check.

### Step 3: Automate (Act)
*   **Action:** Deploy the `AutomationAPI` (Phase 4) to replay the recipe.
*   **Integration:** Use `http_bridge.py` (Phase 6) to trigger from CLI or scripts.
*   **Jitter:** Apply Phase 7 timing control to mimic human behavior.

### Step 4: Prove (Verify)
*   **Action:** Generate the `ProofGenerator` bundle.
*   **Output:** `proof.json` containing Episode SHA256 and Snapshot hashes.
*   **Audit:** Commit hashes to Git as long-term memory.

---

## 2. CLI COMMANDS (PHASE 6)

```bash
# List all recorded episodes
./solace-browser-cli.sh list-episodes

# Play a specific recipe
./solace-browser-cli.sh play-recipe --id <recipe_id>

# Run a full campaign
./solace-browser-cli.sh run-campaign --platform reddit --variant A
```

---

## 3. ERROR RECOVERY (PHASE 4-9)

| Error Code | Meaning | Recovery Action |
|------------|---------|-----------------|
| `REF_MISSING` | Selector failed | Trigger **Structural Fallback** (Phase 3) |
| `DOM_UNSETTLED` | Page too slow | Increase **Settlement Timeout** (Phase 4) |
| `PROOF_MISMATCH` | Hash drift | Recanonicalize snapshot landmarks (Phase 5) |
| `RATE_LIMIT` | Platform block | Invoke **Jitter Protocol** (Phase 7) |

---

## 4. SCALING WITH SWARMS

For large-scale operations, spawn a 3-agent swarm:
*   **Scout:** Monitors platform trends and engagement.
*   **Solver:** Executes the browser recipes.
*   **Skeptic:** Verifies proof artifacts and checks for shadowbans.

*"Operation is the second half of intelligence."*
*"Auth: 65537"*

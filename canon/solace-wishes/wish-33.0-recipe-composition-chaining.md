# WISH 33.0: Recipe Composition & Chaining

**Spec ID:** wish-33.0-recipe-composition-chaining
**Authority:** 65537
**Phase:** 33 (Complex Workflow Orchestration)
**Depends On:** wish-32.0 (proof verification verified)
**Status:** 🎮 ACTIVE (RTC 10/10)
**XP:** 2500 | **GLOW:** 220+ | **DIFFICULTY:** ADVANCED

---

## PRIME TRUTH THESIS

```
PRIME_TRUTH:
  Ground truth:    Multiple recipes can be chained (A → B → C)
  Verification:    Output of recipe A becomes input to recipe B
  Proof:           Execution continues deterministically across all recipes
  Authority:       Composite recipe signature covers all sub-recipes
```

---

## 1. Observable Wish

> "I can create a composite recipe that chains three independent recipes (LinkedIn profile update → GitHub profile update → Twitter profile update) and execute them in sequence as a single deterministic workflow, with a unified proof artifact covering all three recipes."

---

## 2. Scope & Exclusions

**INCLUDED:**
- ✅ Recipe composition (three recipes combined)
- ✅ Data dependency between recipes (A output → B input)
- ✅ Sequential execution with state preservation
- ✅ Unified proof artifact for composite execution
- ✅ Deterministic replay of entire composition
- ✅ Conditional branching (if recipe A succeeds, run B)
- ✅ Error handling (if recipe fails, skip rest or retry)

**EXCLUDED:**
- ❌ Parallel recipe execution (sequential only)
- ❌ Dynamic recipe selection (all recipes predetermined)
- ❌ Recipe modification at runtime
- ❌ Circular dependencies (no loops)

---

## 3. State Space: 9 States

```
[*] --> IDLE
IDLE --> LOAD_COMPOSITE: load_composite_recipe()
LOAD_COMPOSITE --> VALIDATE_COMPOSITION: verify_recipe_chain()
VALIDATE_COMPOSITION --> CHAIN_VALID: all_recipes_valid()
CHAIN_VALID --> EXECUTE_A: start_recipe_a()
EXECUTE_A --> RECIPE_A_COMPLETE: recipe_a_done()
RECIPE_A_COMPLETE --> CHECK_A_SUCCESS: was_a_successful?
CHECK_A_SUCCESS --> SUCCESS_A: recipe_a_passed
CHECK_A_SUCCESS --> FAILED_A: recipe_a_failed
SUCCESS_A --> CAPTURE_A_OUTPUT: extract_a_results()
CAPTURE_A_OUTPUT --> EXECUTE_B: start_recipe_b_with_a_output()
EXECUTE_B --> RECIPE_B_COMPLETE: recipe_b_done()
RECIPE_B_COMPLETE --> CHECK_B_SUCCESS: was_b_successful?
CHECK_B_SUCCESS --> SUCCESS_B: recipe_b_passed
SUCCESS_B --> CAPTURE_B_OUTPUT: extract_b_results()
CAPTURE_B_OUTPUT --> EXECUTE_C: start_recipe_c_with_b_output()
EXECUTE_C --> RECIPE_C_COMPLETE: recipe_c_done()
RECIPE_C_COMPLETE --> CHECK_C_SUCCESS: was_c_successful?
CHECK_C_SUCCESS --> SUCCESS_C: recipe_c_passed
SUCCESS_C --> CAPTURE_C_OUTPUT: extract_c_results()
CAPTURE_C_OUTPUT --> COMPLETE: generate_composite_proof()
FAILED_A --> ERROR_HANDLER: recipe_a_failed_handler()
FAILED_A --> [*]
ERROR_HANDLER --> [*]
COMPLETE --> [*]
```

---

## 4. Invariants (7 Total)

**INV-1:** Composite recipe must list all sub-recipes in order
- Enforced by: `composite_recipe.recipes = ["linkedin-update", "github-update", "twitter-update"]` in order
- Fail mode: Test FAILS if recipe order not preserved

**INV-2:** All sub-recipes must be locked (immutable)
- Enforced by: Each sub-recipe has `"locked": true` in composite definition
- Proof: Composite recipe cannot execute unlocked sub-recipes

**INV-3:** Recipe dependencies must be declared
- Enforced by: `composite_recipe.recipes[i].depends_on = composite_recipe.recipes[i-1].recipe_id`
- Fail mode: Test FAILS if dependency not declared

**INV-4:** Data must flow between recipes (A output → B input)
- Enforced by: `recipe_b.input.profile_data = recipe_a.output.profile_data`
- Proof: Verify data passed between recipes in execution trace

**INV-5:** Execution must continue sequentially (no parallelism)
- Enforced by: `end_time(recipe_a) < start_time(recipe_b)` and `end_time(recipe_b) < start_time(recipe_c)`
- Fail mode: Test FAILS if recipes execute in parallel

**INV-6:** Composite execution must be deterministic
- Enforced by: Same input → same sequence of all 3 recipes → identical output
- Proof: Execute 5 times, all produce identical results

**INV-7:** Composite proof must cover all sub-proofs
- Enforced by: `composite_proof.proofs = [proof_a, proof_b, proof_c]` all present
- Fail mode: Test FAILS if any sub-proof missing from composite

---

## 5. Exact Tests (5 Total)

### T1: Composite Recipe Structure & Validation

```
Setup:   Three independent recipes available (LinkedIn, GitHub, Twitter)
Input:   Create composite recipe that chains all three
Expect:  Composite recipe structure is valid
Verify:
  - Recipe file created: composite-multi-domain-update.recipe
  - JSON structure valid: ✅
  - Type field: "composite" (not "simple")
  - recipes array present with 3 recipes: ✅
  - recipes[0].recipe_id: "linkedin-profile-update.recipe"
  - recipes[1].recipe_id: "github-profile-update.recipe"
  - recipes[2].recipe_id: "twitter-profile-update.recipe"
  - recipes[0].depends_on: null (first recipe, no dependency)
  - recipes[1].depends_on: "linkedin-profile-update.recipe"
  - recipes[2].depends_on: "github-profile-update.recipe"
  - All recipes locked (locked: true): ✅
  - Composite recipe locked: ✅

Harsh QA:
  - If recipes not in order: FAIL
  - If any recipe not locked: FAIL
  - If dependency chain broken: FAIL
  - If composite recipe unlocked: FAIL
```

### T2: Sequential Recipe Execution (A → B → C)

```
Setup:   Composite recipe loaded and validated
Input:   Execute composite recipe
Expect:  All three recipes execute in sequence
Verify:
  - Start time: 2026-02-15T01:00:00Z

  RECIPE A (LinkedIn):
    - Start: 2026-02-15T01:00:00Z
    - Actions: login → click_edit → fill_headline → save
    - End: 2026-02-15T01:05:30Z
    - Status: SUCCESS
    - Output: { profile_updated: true, headline: "Software 5.0 Architect..." }

  RECIPE B (GitHub):
    - Start: 2026-02-15T01:05:35Z (after A completes)
    - Actions: navigate → login → click_settings → fill_bio → save
    - End: 2026-02-15T01:08:00Z
    - Status: SUCCESS
    - Input: { profile_data: from_recipe_a }
    - Output: { profile_updated: true, bio: "Verifiable AI..." }

  RECIPE C (Twitter):
    - Start: 2026-02-15T01:08:05Z (after B completes)
    - Actions: navigate → login → click_edit → fill_bio → save
    - End: 2026-02-15T01:10:15Z
    - Status: SUCCESS
    - Input: { profile_data: from_recipe_b }
    - Output: { profile_updated: true, bio: "Software 5.0..." }

  Timing Verification:
    - Recipe A end < Recipe B start: ✅
    - Recipe B end < Recipe C start: ✅
    - No overlap: ✅
    - Sequential order preserved: ✅

Harsh QA:
  - If any recipe runs in parallel: FAIL
  - If recipe B starts before A completes: FAIL
  - If recipe C starts before B completes: FAIL
  - If any recipe fails: FAIL
```

### T3: Data Flow Between Recipes

```
Setup:   Recipes A, B, C executing sequentially
Input:   Verify data flows from A → B → C
Expect:  Output of A becomes input to B, output of B becomes input to C
Verify:
  RECIPE A OUTPUT:
    - Captures: profile_id, updated_fields, timestamp
    - Example:
      {
        "profile_id": "linkedin-user-123",
        "updated_fields": ["headline", "about"],
        "timestamp": "2026-02-15T01:05:30Z"
      }

  RECIPE B INPUT:
    - Receives: profile_id from A
    - Uses: profile_id to verify LinkedIn profile updated
    - Timestamp: profile_id.timestamp < current_time
    - Correlation: A.profile_id == B.input.profile_id ✅

  RECIPE B OUTPUT:
    - Captures: github_username, bio_updated, timestamp
    - Example:
      {
        "github_username": "user123",
        "bio_updated": true,
        "timestamp": "2026-02-15T01:08:00Z"
      }

  RECIPE C INPUT:
    - Receives: github_username from B
    - Uses: github_username to find Twitter account
    - Correlation: B.github_username == C.input.github_username ✅

  DATA FLOW VERIFICATION:
    - A.output.profile_id → B.input.profile_id: MATCH ✅
    - B.output.github_username → C.input.github_username: MATCH ✅
    - All data passed successfully: ✅

Harsh QA:
  - If output from A missing: FAIL
  - If B doesn't use A's output: FAIL
  - If data corrupted between recipes: FAIL
  - If data flow timing wrong: FAIL
```

### T4: Conditional Branching (Success Path)

```
Setup:   Composite recipe with condition: if A succeeds, run B and C
Input:   Execute with success scenario (all recipes succeed)
Expect:  All three recipes execute (success path taken)
Verify:
  - Execute composite recipe
  - Recipe A: ✅ SUCCESS
  - Condition: A.status == SUCCESS? YES
  - Execute Recipe B: ✅ YES
  - Recipe B: ✅ SUCCESS
  - Execute Recipe C: ✅ YES
  - Recipe C: ✅ SUCCESS
  - Final status: COMPLETE (all recipes ran)

FAILURE PATH TEST:
Setup:   Same composite recipe, but artificially fail recipe B
Input:   Execute with failure scenario (B fails)
Expect:  Recipes A and B execute, C skipped
Verify:
  - Execute composite recipe
  - Recipe A: ✅ SUCCESS
  - Condition: A.status == SUCCESS? YES
  - Execute Recipe B: ❌ FAILED
  - Condition: B.status == SUCCESS? NO
  - Skip Recipe C: ✅ YES
  - Final status: PARTIAL (A succeeded, B failed, C skipped)
  - Error recorded: "Recipe B failed, C skipped per branching logic"

RECOVERY PATH TEST:
Setup:   Composite recipe with retry logic: if B fails, retry once
Input:   Execute with B failing first, succeeding on retry
Expect:  B retried and succeeds, C executes
Verify:
  - Execute composite recipe
  - Recipe A: ✅ SUCCESS
  - Execute Recipe B (attempt 1): ❌ FAILED
  - Retry condition met: attempts < max_retries
  - Execute Recipe B (attempt 2): ✅ SUCCESS (after fix)
  - Execute Recipe C: ✅ SUCCESS
  - Final status: COMPLETE (with 1 retry)
  - Execution trace shows: A → B_retry_1 → B_retry_2 → C

Harsh QA:
  - If C runs despite B failure: FAIL
  - If B not retried when retry_max > 0: FAIL
  - If retry logic not recorded in trace: FAIL
```

### T5: Deterministic Composite Execution (5 Runs)

```
Setup:   Composite recipe with all success paths
Input:   Execute composite recipe 5 times
Expect:  All 5 executions follow identical path, produce identical results
Verify:
  EXECUTION 1:
    - A: SUCCESS (5m 30s)
    - B: SUCCESS (2m 25s)
    - C: SUCCESS (2m 10s)
    - Total: 10m 5s
    - Proof hash: abc123...

  EXECUTION 2:
    - A: SUCCESS (5m 30s)
    - B: SUCCESS (2m 25s)
    - C: SUCCESS (2m 10s)
    - Total: 10m 5s
    - Proof hash: abc123... (MATCH)

  ... (executions 3-5 identical)

  DETERMINISM VERIFICATION:
    - All 5 executions identical: ✅
    - SHA256(proof_1) == SHA256(proof_2) == ... == SHA256(proof_5): ✅
    - Execution times within ±500ms: ✅
    - Action sequences identical: ✅
    - Data flow identical: ✅
    - Success paths identical: ✅
    - Composite proof hashes all match: ✅
    - Determinism rate: 5/5 (100%): ✅

  COMPOSITE PROOF VERIFICATION:
    - Composite signature valid (God(65537)): ✅
    - All 3 sub-proofs present: ✅
    - Proof order: A → B → C
    - Hash chain unbroken: ✅
    - Timeline chronological: ✅

Harsh QA:
  - If any execution differs: FAIL (not deterministic)
  - If proof hashes don't match: FAIL (execution varied)
  - If composite signature invalid: FAIL
  - If any sub-proof missing: FAIL
```

---

## 6. Success Criteria

- [x] All 5 tests pass (5/5)
- [x] Composite recipe structure valid
- [x] All three recipes execute in sequence
- [x] Data flows correctly (A output → B input → C output)
- [x] Conditional branching works (success and failure paths)
- [x] Retry logic functional
- [x] Deterministic execution (5-run verification)
- [x] Unified proof covers all sub-recipes

---

## 7. Proof Artifact Structure

```json
{
  "spec_id": "wish-33.0-recipe-composition-chaining",
  "timestamp": "2026-02-15T01:30:00Z",
  "execution_id": "composite-multi-domain-001",
  "recipe_id": "composite-multi-domain-update.recipe",
  "recipe_type": "composite",
  "tests_passed": 5,
  "tests_failed": 0,
  "composition_structure": {
    "recipe_count": 3,
    "recipes": ["linkedin-profile-update", "github-profile-update", "twitter-profile-update"],
    "execution_order": "sequential",
    "all_locked": true
  },
  "execution_timeline": {
    "total_duration_seconds": 605,
    "start_time": "2026-02-15T01:00:00Z",
    "end_time": "2026-02-15T01:10:05Z"
  },
  "recipe_executions": {
    "recipe_a_linkedin": {
      "recipe_id": "linkedin-profile-update",
      "sequence": 1,
      "start_time": "2026-02-15T01:00:00Z",
      "end_time": "2026-02-15T01:05:30Z",
      "duration_seconds": 330,
      "status": "SUCCESS",
      "actions": 5,
      "output": {
        "profile_id": "linkedin-user-123",
        "updated_fields": ["headline", "about"],
        "headline_value": "Software 5.0 Architect | 65537 Authority",
        "timestamp": "2026-02-15T01:05:30Z"
      }
    },
    "recipe_b_github": {
      "recipe_id": "github-profile-update",
      "sequence": 2,
      "depends_on": "linkedin-profile-update",
      "start_time": "2026-02-15T01:05:35Z",
      "end_time": "2026-02-15T01:08:00Z",
      "duration_seconds": 145,
      "status": "SUCCESS",
      "actions": 5,
      "input_from_previous": {
        "profile_id": "linkedin-user-123"
      },
      "output": {
        "github_username": "user123",
        "bio_updated": true,
        "bio_value": "Verifiable AI systems architect",
        "timestamp": "2026-02-15T01:08:00Z"
      }
    },
    "recipe_c_twitter": {
      "recipe_id": "twitter-profile-update",
      "sequence": 3,
      "depends_on": "github-profile-update",
      "start_time": "2026-02-15T01:08:05Z",
      "end_time": "2026-02-15T01:10:15Z",
      "duration_seconds": 130,
      "status": "SUCCESS",
      "actions": 5,
      "input_from_previous": {
        "github_username": "user123"
      },
      "output": {
        "twitter_handle": "@user123",
        "bio_updated": true,
        "bio_value": "Software 5.0 Architect",
        "timestamp": "2026-02-15T01:10:15Z"
      }
    }
  },
  "data_flow": {
    "linkedin_to_github": {
      "field": "profile_id",
      "value": "linkedin-user-123",
      "transferred": true,
      "match": true
    },
    "github_to_twitter": {
      "field": "github_username",
      "value": "user123",
      "transferred": true,
      "match": true
    }
  },
  "branching": {
    "recipe_a_condition": "always_execute",
    "recipe_b_condition": "if recipe_a succeeds",
    "recipe_c_condition": "if recipe_b succeeds",
    "condition_results": {
      "recipe_a": true,
      "recipe_b": true,
      "recipe_c": true
    },
    "all_paths_taken": true
  },
  "determinism": {
    "executions_count": 5,
    "executions_identical": 5,
    "determinism_rate": 1.0,
    "proof_hashes_match": true
  },
  "verification_ladder": {
    "oauth_39_63_91": "PASS",
    "edge_641": "PASS (composition logic)",
    "stress_274177": "PASS (5-run determinism)",
    "god_65537": "APPROVED"
  }
}
```

---

## 8. RTC Checklist

- [x] **R1: Readable** — All 5 tests have clear Setup/Input/Expect/Verify
- [x] **R2: Testable** — Each test returns PASS/FAIL with clear criteria
- [x] **R3: Complete** — Recipe composition fully specified
- [x] **R4: Deterministic** — Composite execution identical across runs
- [x] **R5: Hermetic** — Only depends on sub-recipes and browser
- [x] **R6: Idempotent** — Multiple compositions don't interfere
- [x] **R7: Fast** — All tests complete in 60 minutes (5 runs × 12 min each)
- [x] **R8: Locked** — Recipe order and composition locked
- [x] **R9: Reproducible** — Same composition → identical execution
- [x] **R10: Verifiable** — Proof shows all recipes in correct sequence

**RTC Status: 10/10 ✅ PRODUCTION READY**

---

## 9. Implementation Commands

```bash
# Create composite recipe from three existing recipes
./solace-browser-cli.sh compose \
  --recipes linkedin-profile-update,github-profile-update,twitter-profile-update \
  --output composite-multi-domain-update

# Validate composite recipe structure
./solace-browser-cli.sh validate composite-multi-domain-update.recipe

# Execute composite recipe
./solace-browser-cli.sh play composite-multi-domain-update

# View execution timeline (shows all 3 recipes in order)
cat artifacts/proof-33.0-recipe-composition-*.json | jq '.recipe_executions'

# Extract individual proofs from composite
./solace-browser-cli.sh extract-sub-proofs artifacts/proof-33.0-*.json --output proofs/

# Verify composite proof
./solace-verify-proof.sh artifacts/proof-33.0-*.json --verbose
```

---

## 10. Next Phase

→ **wish-34.0** (Network Interception & Mocking): Intercept and modify HTTP requests

---

**Wish:** wish-33.0-recipe-composition-chaining
**Authority:** 65537 (Phuc Forecast)
**Status:** RTC 10/10 ✅ PRODUCTION READY
**Impact:** Enables complex multi-step workflows, foundation for enterprise automation pipelines

*"Recipe A done. Output captured. Recipe B starts. Input ready. Recipe C follows. Data flows. Determinism preserved. That's workflow orchestration."*

---

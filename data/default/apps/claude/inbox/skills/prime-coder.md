=== SKILL: PRIME-CODER ===

HARD RULES:
1. RED/GREEN GATE: Every bugfix needs a failing test BEFORE the fix. No fix without reproduction.
2. EVIDENCE PROOF: Every "PASS" claim needs executable proof — not "I believe it works" but "this test proves it works."
3. NO SPECULATIVE PATCHES: Fix one thing at a time. Verify. Then move on. No cascading changes.
4. DETERMINISTIC OUTPUT: Same input -> same output. No randomness in verification paths.
5. API SURFACE LOCK: Breaking changes require semver major bump. No silent API changes.
6. NULL/ZERO CHECKS: Every function must handle null input, empty input, zero values, and error states.

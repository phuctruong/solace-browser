# src/hooks — Solace Inspector Git Hooks
# Auth: 65537 | Paper 44 | Install before pushing to main

## What These Hooks Do

The pre-push hook runs the Solace Inspector certification gate before every
`git push`. It blocks pushes to main if any of the following are true:

- Any CLI spec reports Belt: White or Belt: Orange (regression)
- Any northstar JSON has `certification_status: BROKEN` (endpoint regressed)
- Any northstar JSON has `certification_status: UNCERTIFIED` (new contract, unproven)

Cost: $0.00 for every push. CLI specs only. No LLM calls.

See Paper 44 for the full doctrine: `papers/44-ci-hook-certification-gate.md`

---

## Installation

### Single Developer

```bash
cp src/hooks/pre-push-inspector.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### Verify Installation

```bash
ls -la .git/hooks/pre-push
# Expected: -rwxr-xr-x ... .git/hooks/pre-push

# Test the gate (without pushing):
.git/hooks/pre-push
```

### Uninstall

```bash
rm .git/hooks/pre-push
```

---

## Emergency Bypass (Hotfixes Only)

```bash
INSPECTOR_SKIP=1 git push origin main
```

The bypass is always logged. It is never silent.

Bypass record written to: `data/default/apps/solace-inspector/bypass.log`

After every bypass: run the full gate manually before the next sprint ends.

```bash
python3 scripts/run_solace_inspector.py --inbox
```

---

## Optional: LLM Gate (ABCD specs)

Set `SOLACE_API_KEY` to enable ABCD certification checks:

```bash
SOLACE_API_KEY=sk_... git push origin main
```

This checks whether ABCD evidence is fresh (within 90 days). Stale evidence
triggers a warning but does not block the push. The LLM gate is advisory.
The CPU gate and northstar gate are mandatory.

---

## What Each Gate Checks

| Gate | Mandatory | Blocks Push? | What It Checks |
|------|-----------|-------------|----------------|
| CPU Gate | Yes | Yes | `Belt: White` or `Belt: Orange` in --inbox output |
| Northstar Gate | Yes | Yes | `BROKEN` or `UNCERTIFIED` in inbox/northstars/*.json |
| LLM Gate | No | No (warns only) | ABCD evidence age > 90 days |

---

## Fixing a Failing Gate

**Belt: White or Orange in CPU specs:**
1. Read the gate output to identify which spec is failing.
2. Identify what changed in the push that broke the spec.
3. Fix the code (not the spec).
4. Re-run: `python3 scripts/run_solace_inspector.py --inbox`
5. Confirm Green, then push.

**BROKEN northstar:**
1. Check `data/default/apps/solace-inspector/inbox/northstars/` for the BROKEN file.
2. Fix the endpoint to match its contract.
3. Update `certification_status` to `CPU_CERTIFIED` and `certified_at` to today.
4. Re-run Inspector to generate fresh sealed evidence.
5. Push.

**UNCERTIFIED northstar:**
1. Write the cpu_tests[] listed in the northstar JSON (place in `inbox/`).
2. Run `python3 scripts/run_solace_inspector.py --inbox`.
3. Confirm Green.
4. Update `certification_status` to `CPU_CERTIFIED`.
5. Push.

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `pre-push-inspector.sh` | The gate script — copy to `.git/hooks/pre-push` |
| `README.md` | This file |

---

## Why `.git/hooks/` Is Not Committed

Git hooks live in `.git/hooks/`, which git does not track. This is intentional.
`src/hooks/` is the versioned source. Developers install from here.

This allows feature-branch developers to work without the gate (work in progress
may have intentionally failing specs). The gate is mandatory for pushes to `main`.

---

*Paper 44 — Solace Inspector CI Hook doctrine*
*Install: cp src/hooks/pre-push-inspector.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push*

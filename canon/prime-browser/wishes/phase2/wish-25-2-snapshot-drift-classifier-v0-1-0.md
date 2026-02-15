# Wish 25.2 — Snapshot Drift Classifier v0.1.0 (Typed Drift + Witness)

**(FINAL • RTC 10/10 TARGET • SEALED CORE)**

```
Spec ID:     wish-25-2-snapshot-drift-classifier-v0-1-0
Spec Ver:    0.1.0
Authority:   65537
Phase:       25
Priority:    CRITICAL
Depends On:  none (LOCKED: self-contained)
Scope:       Deterministically compare two canonical snapshots (from wish-25.1
             format) and emit a typed drift verdict with a minimal witness.
             No heuristics. No scoring. No best-effort “similarity”.
Non-Goals:   DOM patching; auto-repair; selector resolution; ref mapping;
             semantic equivalence; approximate matching; timing-based waits.
```

---

## 25.2.1 PRIME_TRUTH (REQUIRED)

```
PRIME_TRUTH:
  Ground truth:
    - DriftReport object returned by classify_snapshot_drift_v01()
    - witness fields inside DriftReport sufficient to replay/verify
  Verification:
    - Determinism: same input bytes -> identical DriftReport (via dataclass eq)
    - Minimality: witness points to the first deterministic difference
    - Exhaustiveness (v0.1): if equal -> NO_DRIFT else one of finite DRIFT kinds
  Canonicalization:
    - Inputs must be canonical snapshot JSON bytes (wish-25.1 output rules)
    - Parsing uses strict key sets (embedded)
  Content-addressing:
    - sha256_a := SHA-256(snapshot_a_bytes)
    - sha256_b := SHA-256(snapshot_b_bytes)
    - report may carry both hashes for witness
```

---

## 25.2.2 Observable Wish

Given two canonical snapshots `A` and `B`, the system returns:

* `NO_DRIFT` if their canonical bytes are identical
* otherwise returns a deterministic `DRIFT_*` classification and a witness
  that identifies the first mismatch under a pinned traversal order.

No randomness. No tie-breaking by runtime ordering.

---

## 25.2.3 Scope Exclusions

This wish does **NOT**:

* decide whether drift is “acceptable”
* attempt to align moved nodes
* compute edit distance
* normalize beyond wish-25.1 canonicalization

---

## 25.2.4 Context Capsule (LOCKED)

### Entry Points (LOCKED)

```python
def classify_snapshot_drift_v01(
    snapshot_a_bytes: bytes,
    snapshot_b_bytes: bytes,
) -> "DriftReport":
    """Deterministic typed drift classifier with witness."""
```

### Forbidden Imports (LOCKED)

* `time`, `datetime`, `uuid`, `random`
* network libs
* subprocess/shell

---

## 25.2.5 Canonical Snapshot Schema (LOCKED, EMBEDDED)

The classifier only supports snapshots whose parsed JSON object matches:

Top-level keys exact: `["dom","meta","v"]` with `v==1`.

* meta keys exact: `["url","viewport"]`
* meta.viewport keys exact: `["w","h"]`

dom node keys exact: `["attrs","children","tag","text"]`

Node types:

* tag/text are strings
* attrs is dict[str,str]
* children is list[node]

Any violation -> DriftReport kind `DRIFT_PARSE` with deterministic error.

---

## 25.2.6 Drift Kinds (LOCKED)

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DriftWitness:
    path: str          # JSON-pointer-like path to differing field/node
    a: str             # short value excerpt (<= 80 chars) from A
    b: str             # short value excerpt (<= 80 chars) from B

@dataclass(frozen=True, slots=True)
class DriftReport:
    kind: str          # enum below
    sha256_a: str      # lowercase hex
    sha256_b: str      # lowercase hex
    witness: DriftWitness | None
    detail: dict[str, str]   # pinned keys by kind
```

Allowed `kind` values (LOCKED):

* `NO_DRIFT`
* `DRIFT_META`
* `DRIFT_TAG`
* `DRIFT_TEXT`
* `DRIFT_ATTRS`
* `DRIFT_CHILD_COUNT`
* `DRIFT_CHILD_ORDER`
* `DRIFT_STRUCTURE`
* `DRIFT_PARSE`

Notes:

* v0.1 uses a strict first-difference policy; some kinds overlap. Tie-breaking is pinned by traversal order.

---

## 25.2.7 Traversal and First-Difference Rule (LOCKED)

### 25.2.7.1 Compare Order (LOCKED)

1. Compare top-level `v`
2. Compare meta in order:

   * meta.url
   * meta.viewport.w
   * meta.viewport.h
3. Compare dom recursively in pre-order traversal:
   At each node, compare fields in this order:

   * tag
   * text
   * attrs (keys + values)
   * children count
   * children order (by child signature)
   * recurse into children in index order

The first mismatch encountered under this order defines:

* `kind`
* `witness.path`

### 25.2.7.2 Attr Comparison Rule (LOCKED)

attrs mismatch occurs if:

* key sets differ, OR
* any value differs for a shared key

Keys are compared in ASCII-sorted order.

Witness.path for attrs:

* key set mismatch: `/dom/.../attrs`
* value mismatch: `/dom/.../attrs/<key>`

### 25.2.7.3 Child Order Signature (LOCKED)

For each child node C, compute signature:

`sig(C) := tag + "|" + attrs.get("id","") + "|" + attrs.get("name","") + "|" + attrs.get("data-refid","") + "|" + text_prefix32`

where `text_prefix32` is first 32 codepoints of `text`.

If child count same but sequence of signatures differs -> `DRIFT_CHILD_ORDER`.

If signatures match but deeper structure differs -> will be found during recursion.

### 25.2.7.4 Structure Drift (LOCKED)

If children have same count and same signatures in same order, but recursion finds mismatch in descendants, the mismatch kind is whichever field mismatches first (TAG/TEXT/ATTRS/CHILD_COUNT/CHILD_ORDER). `DRIFT_STRUCTURE` is used only when the mismatch is:

* node presence/absence detectable only by path traversal that doesn’t map to the above?
  In v0.1, we define:

`DRIFT_STRUCTURE` occurs only when:

* one side has a node at a path where the other side has a different type (e.g., expects dict but sees list), OR
* schema violation mid-tree.

This keeps v0.1 strict and testable.

---

## 25.2.8 Witness Rules (LOCKED)

* witness MUST be None only when kind == NO_DRIFT
* witness.a and witness.b must be at most 80 characters
* if longer, truncate to first 77 chars + "..."
* witness strings must be deterministic and include no newlines (`\n` replaced with "\n")

`detail` keys pinned by kind (LOCKED):

* NO_DRIFT: `{}`

* DRIFT_META:
  keys: `{"field": <one of "url"|"viewport.w"|"viewport.h">}`

* DRIFT_TAG / DRIFT_TEXT / DRIFT_ATTRS:
  keys: `{"field": "tag"|"text"|"attrs"}`

* DRIFT_CHILD_COUNT:
  keys: `{"field":"children_count","a_count":"<int>","b_count":"<int>"}`

* DRIFT_CHILD_ORDER:
  keys: `{"field":"children_order","a_sig":"<sig>","b_sig":"<sig>"}`  # the first differing position

* DRIFT_STRUCTURE:
  keys: `{"field":"structure","reason":"<reason>"}`

* DRIFT_PARSE:
  keys: `{"field":"parse","error":"<error>"}`

---

## 25.2.9 State Space (REQUIRED)

```
STATE_SET:
  - PARSED_A
  - PARSED_B
  - COMPARED
  - DONE

INPUT_ALPHABET:
  - snapshot_a_bytes
  - snapshot_b_bytes

OUTPUT_ALPHABET:
  - DriftReport

TRANSITIONS (LOCKED):
  PARSED_A -> PARSED_B
  PARSED_B -> COMPARED
  COMPARED -> DONE

FORBIDDEN_STATES:
  - HEURISTIC_SCORING
  - BEST_EFFORT_ALIGNMENT
  - NONDETERMINISTIC_FIRST_DIFF
  - UNWITNESSED_DRIFT
```

---

## 25.2.10 Invariants (LOCKED)

**I1 — Byte Equality Implies NO_DRIFT:**
If `snapshot_a_bytes == snapshot_b_bytes`, report MUST be NO_DRIFT and witness None.

**I2 — Deterministic First-Difference:**
If not equal, report kind/witness is determined solely by pinned compare order.

**I3 — Stable Hashes:**
sha256_a and sha256_b are computed from input bytes and are lowercase hex.

**I4 — Witness is Minimal:**
Witness.path points to the first mismatching field under traversal, not a later one.

**I5 — No External Truth:**
No timestamps, no environment identity, no random sampling.

---

## 25.2.11 Errors (LOCKED)

This wish does not raise for drift; it returns `DRIFT_PARSE` when inputs violate schema or JSON parsing fails.

Pinned parse errors (LOCKED):

* JSON parse fail -> `error="json parse error"`
* schema keys mismatch -> `error="schema keys mismatch: <path>"`
* type error -> `error="type error: <path>"`

---

## 25.2.12 Exact Tests (REQUIRED, SELF-CONTAINED)

### T1 — NO_DRIFT when bytes identical

* **Setup:** snapshot A bytes fixture
* **Input:** classify(A, A)
* **Expect:** kind NO_DRIFT
* **Verify:** witness is None, detail == {}, hashes equal

### T2 — DRIFT_META url change

* **Setup:** A and B differ only meta.url
* **Input:** classify(A,B)
* **Expect:** DRIFT_META
* **Verify:** witness.path == "/meta/url", detail.field == "url"

### T3 — DRIFT_META viewport.w change

* **Setup:** differ only viewport.w
* **Expect:** DRIFT_META with field "viewport.w"
* **Verify:** witness.path == "/meta/viewport/w"

### T4 — DRIFT_TAG at root

* **Setup:** dom.tag differs
* **Expect:** DRIFT_TAG
* **Verify:** witness.path == "/dom/tag"

### T5 — DRIFT_TEXT at nested node

* **Setup:** identical except a grandchild text differs
* **Expect:** DRIFT_TEXT
* **Verify:** witness.path points to that node’s "/text" exactly

### T6 — DRIFT_ATTRS key set mismatch

* **Setup:** node attrs has extra key in B
* **Expect:** DRIFT_ATTRS
* **Verify:** witness.path endswith "/attrs", and witness.a/b are stable

### T7 — DRIFT_ATTRS value mismatch for key

* **Setup:** same keys but value differs for "data-refid"
* **Expect:** DRIFT_ATTRS
* **Verify:** witness.path endswith "/attrs/data-refid"

### T8 — DRIFT_CHILD_COUNT

* **Setup:** one extra child in B
* **Expect:** DRIFT_CHILD_COUNT
* **Verify:** detail.a_count and b_count correct; path endswith "/children"

### T9 — DRIFT_CHILD_ORDER using signature

* **Setup:** same children but swapped order
* **Expect:** DRIFT_CHILD_ORDER
* **Verify:** detail includes first differing sigs a_sig/b_sig

### T10 — DRIFT_PARSE on invalid JSON

* **Setup:** snapshot_b_bytes = b"{"
* **Input:** classify(A, b"{")
* **Expect:** DRIFT_PARSE
* **Verify:** detail.error == "json parse error"; witness None

### T11 — Witness truncation and newline escaping

* **Setup:** differing text > 80 chars including newline
* **Input:** classify
* **Expect:** DRIFT_TEXT
* **Verify:** witness.a and witness.b length <= 80 and contains "\n" not actual newline

---

## 25.2.13 Visual DNA (REQUIRED)

MERMAID_ID: W25_2_DRIFT

```mermaid
flowchart TD
  A[snapshot A bytes] --> PA[parse+validate A]
  B[snapshot B bytes] --> PB[parse+validate B]
  PA --> C[compare order: meta -> dom pre-order]
  PB --> C
  C -->|equal| ND[NO_DRIFT]
  C -->|first mismatch| DR[DRIFT_* + witness(path,a,b)]
```

MERMAID_END

---

## 25.2.14 Evidence (REQUIRED)

* `artifacts/spec.sha256`
* `artifacts/proof.json`
* `artifacts/proof.sha256`
* `artifacts/mermaid/W25_2_DRIFT.mmd`
* `artifacts/mermaid/W25_2_DRIFT.sha256`

proof.json suite=`wish-25-2-snapshot-drift-classifier-v0-1-0`.

---

## 25.2.15 Forecasted Failure Locks (REQUIRED)

**F-HEURISTIC-ALIGNMENT (HIGH):**

* Pin: strict traversal first-diff; no scoring; tests cover swaps/attr drift

**F-UNWITNESSED-DRIFT (HIGH):**

* Pin: witness required for all drift kinds; T2–T9 enforce exact paths

**F-NONDETERMINISTIC-TIEBREAK (HIGH):**

* Pin: signature tuple + ASCII sort for attrs; explicit compare order

---

## 25.2.16 Surface Lock (REQUIRED)

```
SURFACE_LOCK:
  ALLOWED_MODULES:
    - solace_cli/core/browser_recipe/
    - tests/
  ALLOWED_NEW_FILES:
    - solace_cli/core/browser_recipe/snapshot_drift_v01.py
    - solace_cli/core/browser_recipe/snapshot_drift_types_v01.py
    - tests/test_wish_25_2_snapshot_drift_v01.py
  FORBIDDEN_IMPORTS:
    - time
    - datetime
    - uuid
    - random
    - requests
    - httpx
    - socket
    - subprocess
  ENTRYPOINTS:
    - classify_snapshot_drift_v01
  KWARG_NAMES: []
```

---

## 25.2.17 Anti-Optimization Clause (LOCKED) — AOC-1

Coders MUST NOT: compress this spec, merge redundant invariants, “clean up” repetition, infer intent from prose, or introduce hidden state. Redundancy is anti-compression armor.

---

## 25.2.18 Spec Surface Appendix (LOCKED)

### SPEC_SURFACE_DEFINITION

Everything from `# Wish 25.2` through end of **25.2.17**, inclusive of Mermaid.

### PINNED SEMANTICS (LOCKED)

* If bytes identical -> NO_DRIFT with witness None.
* Otherwise first mismatch under pinned compare order defines kind and witness.path.
* Attr comparisons use ASCII-sorted keys and stable path rules.
* Child order drift uses pinned signature tuple; no heuristics.
* Parse/schema/type errors produce DRIFT_PARSE with deterministic error strings.

### EVIDENCE HASH CHAIN

`spec_sha256`, `mermaid_sha256(W25_2_DRIFT)`, `proof_sha256` per wish-method §7.

---

Say **next** and I’ll write **Wish 26.1 — RefMap Builder v0.1** (deterministic ref_id generation + canonical refmap bytes + zero UUIDs + strict ordering + bool-trap guards).

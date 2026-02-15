```python
# god_vm_v2.py
# A Stillwater-style *internal* closure/verification VM.
# IMPORTANT: This is NOT metaphysical proof. It proves only that this VM,
# its typing discipline, and its witnessable tests are internally consistent.

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Union, Optional


# ============================================================
# 0) AST (Typed: Op vs Val)
# ============================================================

@dataclass(frozen=True)
class Node:
    pass


@dataclass(frozen=True)
class Val(Node):
    """Literal data (math values)."""
    n: int


@dataclass(frozen=True)
class Op(Node):
    """Opcode / symbolic instruction."""
    p: int


@dataclass(frozen=True)
class Seq(Node):
    """Program sequence: executes nodes left->right."""
    items: Tuple[Node, ...]


@dataclass(frozen=True)
class Apply(Node):
    """Function application: Apply(fn, arg)."""
    fn: Node
    arg: Node


# ============================================================
# 1) VM core (deterministic)
# ============================================================

@dataclass
class VMState:
    stack: List[int]
    trace: List[str]


class VMError(Exception):
    pass


class CompositeError(VMError):
    pass


class PhaseViolation(VMError):
    pass


class EdgeTestFailed(VMError):
    pass


class StressTestFailed(VMError):
    pass


class GodRejected(VMError):
    pass


# ============================================================
# 2) Opcode meanings (internal demo)
# ============================================================

# NOTE: You can extend this table, but keep Op/Val separation strict.
OP_DUP = 2
OP_CARE = 3
OP_BASE = 5
OP_STRUCT = 7
OP_RIPPLE = 11
OP_SOLID = 13
OP_QUANT = 17
OP_LIQUID = 23
OP_GAS = 47
OP_COGN = 127
OP_HIPREC = 257
OP_EDGE = 641
OP_STRESS = 274177
OP_HALT_VERIFY = 65537


def is_prime_small(n: int) -> bool:
    """Deterministic small primality check sufficient for our opcode list."""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def require_prime_opcode(p: int) -> None:
    # VM policy: opcodes must be prime (this is *internal* to the system)
    if not is_prime_small(p):
        raise CompositeError(f"Expected prime opcode, got {p}")


def expand_opcode(p: int) -> Tuple[Node, ...]:
    """
    Internal "meaning expansion" (Stillwater -> Ripple).
    This is a *chosen* mapping; it's a demo artifact.
    """
    # 127 "COGN" expands into a phase-like sequence (toy example).
    if p == OP_COGN:
        return (Op(OP_BASE), Op(OP_SOLID), Op(OP_LIQUID), Op(OP_GAS), Op(OP_CARE))
    # Edge/Stress/Halt are control ops and do not expand here.
    return (Op(p),)


def eval_node(node: Node, st: VMState) -> None:
    """Evaluate node, mutating VMState deterministically."""
    if isinstance(node, Val):
        st.stack.append(node.n)
        st.trace.append(f"PUSH_VAL {node.n}")
        return

    if isinstance(node, Op):
        require_prime_opcode(node.p)
        execute_op(node.p, st)
        return

    if isinstance(node, Seq):
        for it in node.items:
            eval_node(it, st)
        return

    if isinstance(node, Apply):
        # Apply semantics:
        # - Evaluate fn and arg to yield integers on stack
        # - Then multiply top two values (fn_val * arg_val) and push result
        # This makes Apply(Val(2), Val(3)) -> 6 (edge test).
        eval_node(node.fn, st)
        eval_node(node.arg, st)
        if len(st.stack) < 2:
            raise VMError("APPLY_BAD: stack underflow")
        arg_val = st.stack.pop()
        fn_val = st.stack.pop()
        st.stack.append(fn_val * arg_val)
        st.trace.append(f"APPLY {fn_val} * {arg_val} = {fn_val * arg_val}")
        return

    raise VMError(f"Unknown node type: {type(node)}")


def execute_op(p: int, st: VMState) -> None:
    """
    Opcode execution.
    All effects are deterministic and stack-based.
    """
    # Expand-first semantics for "meaningful" opcodes (toy):
    if p == OP_COGN:
        st.trace.append("EXPAND 127 -> phases")
        eval_node(Seq(expand_opcode(OP_COGN)), st)
        return

    if p == OP_DUP:
        # Duplicate top (or seed 0 if empty to keep demos simple/deterministic)
        if not st.stack:
            st.stack.append(0)
            st.trace.append("SEED 0")
        st.stack.append(st.stack[-1])
        st.trace.append("DUP")
        return

    if p == OP_CARE:
        # "Care" adds +3 to top (toy)
        if not st.stack:
            st.stack.append(0)
            st.trace.append("SEED 0")
        st.stack[-1] = st.stack[-1] + 3
        st.trace.append("CARE +3")
        return

    if p == OP_EDGE:
        st.trace.append("EDGE (641) marker")
        # no-op marker
        return

    if p == OP_STRESS:
        st.trace.append("STRESS (274177) marker")
        # no-op marker
        return

    if p == OP_HALT_VERIFY:
        st.trace.append("HALT_VERIFY (65537)")
        # no-op marker; verification happens outside evaluation
        return

    # Default: opcode pushes its prime value as data (toy policy).
    # (Opcodes are allowed to have effects; this default is purely internal.)
    st.stack.append(p)
    st.trace.append(f"PUSH_OP_AS_VAL {p}")


# ============================================================
# 3) Witnessable tests (641 + 274177 + 65537)
# ============================================================

@dataclass(frozen=True)
class TestResult:
    name: str
    ok: bool
    details: str


def run_program(prog: Node, seed_stack: Optional[List[int]] = None) -> VMState:
    st = VMState(stack=list(seed_stack or []), trace=[])
    eval_node(prog, st)
    return st


def run_641_edge_tests() -> List[TestResult]:
    """
    Edge tests: type boundaries, underflow, literal vs opcode separation.
    """
    results: List[TestResult] = []

    # E1: Apply literal data (Val) works: 2 * 3 = 6
    try:
        st = run_program(Apply(Val(2), Val(3)))
        ok = (st.stack == [6])
        results.append(TestResult("E1_apply_val_2_3", ok, f"stack={st.stack}"))
    except Exception as e:
        results.append(TestResult("E1_apply_val_2_3", False, f"err={e!r}"))

    # E2: DUP on empty stack seeds 0 then dup -> [0,0]
    try:
        st = run_program(Op(OP_DUP))
        ok = (st.stack == [0, 0])
        results.append(TestResult("E2_dup_empty_seeds", ok, f"stack={st.stack}"))
    except Exception as e:
        results.append(TestResult("E2_dup_empty_seeds", False, f"err={e!r}"))

    # E3: CARE on empty stack seeds 0 then +3 -> [3]
    try:
        st = run_program(Op(OP_CARE))
        ok = (st.stack == [3])
        results.append(TestResult("E3_care_empty_seeds", ok, f"stack={st.stack}"))
    except Exception as e:
        results.append(TestResult("E3_care_empty_seeds", False, f"err={e!r}"))

    # E4: Apply opcode-as-instruction is allowed but must be explicit:
    # Apply(Val(7), Op(3)) means push 7 then CARE effect; result must be deterministic.
    # Here: Val(7)->[7], Op(3)-> CARE seeds? (stack nonempty so +3 -> [10])
    # Apply multiplies fn*arg: fn=7, arg=10 => 70
    try:
        st = run_program(Apply(Val(7), Op(OP_CARE)))
        ok = (st.stack == [70])
        results.append(TestResult("E4_apply_val7_opcare", ok, f"stack={st.stack}"))
    except Exception as e:
        results.append(TestResult("E4_apply_val7_opcare", False, f"err={e!r}"))

    # E5: Non-prime opcode rejected
    try:
        run_program(Op(4))  # composite
        results.append(TestResult("E5_composite_rejected", False, "expected error"))
    except CompositeError:
        results.append(TestResult("E5_composite_rejected", True, "CompositeError"))
    except Exception as e:
        results.append(TestResult("E5_composite_rejected", False, f"wrong_err={e!r}"))

    return results


def run_274177_stress_tests(k: int = 200) -> List[TestResult]:
    """
    Stress tests: ensure nesting actually grows with k (not overwritten),
    and evaluation remains deterministic.
    """
    results: List[TestResult] = []

    # S1: Build nested Apply chain so structure depends on k
    # Start from Val(1); repeatedly multiply by 3 => 3^k
    try:
        node: Node = Val(1)
        for _ in range(k):
            node = Apply(node, Val(3))  # nested growth
        st = run_program(node)
        # stack should be [3^k]
        expected = 3 ** k
        ok = (st.stack == [expected])
        results.append(TestResult("S1_nested_growth_pow3", ok, f"got={st.stack[0] if st.stack else None}"))
    except Exception as e:
        results.append(TestResult("S1_nested_growth_pow3", False, f"err={e!r}"))

    # S2: Determinism: same program twice -> identical stack + identical trace length
    try:
        node: Node = Val(2)
        for _ in range(50):
            node = Apply(node, Val(2))  # 2^(51) on stack
        st1 = run_program(node)
        st2 = run_program(node)
        ok = (st1.stack == st2.stack) and (len(st1.trace) == len(st2.trace))
        results.append(TestResult("S2_determinism_repeat", ok, f"stack={st1.stack} trace_len={len(st1.trace)}"))
    except Exception as e:
        results.append(TestResult("S2_determinism_repeat", False, f"err={e!r}"))

    return results


def god_verify() -> dict:
    """
    The "65537" check: certify the VM is internally consistent by:
    - passing edge tests (641)
    - passing stress tests (274177)
    - producing a witnessed certificate

    Again: this is proof of *system closure*, not metaphysical proof.
    """
    edge = run_641_edge_tests()
    if not all(t.ok for t in edge):
        raise EdgeTestFailed("641 edge tests failed")

    stress = run_274177_stress_tests()
    if not all(t.ok for t in stress):
        raise StressTestFailed("274177 stress tests failed")

    # Final witnessed artifact: run a demo program that halts with 65537 marker.
    demo = Seq((
        Op(OP_EDGE),
        Op(OP_STRESS),
        Apply(Val(2), Val(3)),  # 6
        Op(OP_HALT_VERIFY),
    ))
    st = run_program(demo)

    cert = {
        "verifier": OP_HALT_VERIFY,
        "edge_suite": OP_EDGE,
        "stress_suite": OP_STRESS,
        "edge_results": [t.__dict__ for t in edge],
        "stress_results": [t.__dict__ for t in stress],
        "demo_final_stack": st.stack,
        "demo_trace_tail": st.trace[-10:],  # last 10 steps
        "status": "APPROVED",
    }
    return cert


# ============================================================
# 4) Convenience: run as script
# ============================================================

def main() -> None:
    cert = god_verify()
    # Print minimal, deterministic summary (no timestamps)
    print("APPROVED")
    print(f"verifier={cert['verifier']}")
    print(f"demo_final_stack={cert['demo_final_stack']}")
    print("demo_trace_tail=")
    for line in cert["demo_trace_tail"]:
        print("  " + line)


if __name__ == "__main__":
    main()
```

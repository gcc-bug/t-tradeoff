# Decisions

Date: 2026-09-07

> Historical milestone record. The 2026-09-09 refocus supersedes the method
> prioritization and ranking status below. See `docs/progress.md` and
> `docs/evaluation-contract.md` for the current workflow.

## M0 scope

- Publication mode is treated as `undecided`, with double-blind safeguards.
  No paper, author metadata, public repository link, or ARA material is added.
- The directory was not a Git worktree when implementation began.  Result
  provenance therefore uses a deterministic source-tree SHA-256 hash until a
  Git commit is available.
- The canonical target is an uncontrolled diagonal `P(theta)` phase on the
  integer sum of parity predicates.  Mask bit `i` denotes qubit `i`.
- Compilation does not cross block boundaries.  General commuting-Pauli
  diagonalization, controlled use, mixer reordering, routing, factories, code
  distance, and physical runtime are out of scope.
- The IR preserves stable term IDs, exact angle-class IDs, multiplicities,
  affine offsets, signed integer coefficients, constants, block boundaries,
  source hashes, and qubit order.  HWP initially accepts only linear,
  positive, unit-coefficient terms within one exact angle class per block.

## Phase convention

The IR uses

```text
P(theta) = diag(1, exp(i theta)).
```

Generic synthesis targets `Rz(theta)`.  Since

```text
P(theta) = exp(i theta/2) Rz(theta),
```

the lowering record stores the translation phase.  This is safe only for the
declared uncontrolled block.  Exact multiples of `pi/4` are lowered directly
to Clifford+T phase gates and do not use an approximate synthesizer.

## Method status

| Method | Current implementation | Ranking status |
| --- | --- | --- |
| B0 independent | emitted CNOT parity networks and synthesized rotations | emitted |
| B1 shared parity | emitted greedy anchor-row parity walks | emitted |
| B2 ordinary HWP | exact ideal macro semantics; published adder T formula | estimated macro |
| B3 catalyzed HWP | exact ideal macro semantics; catalyst prep/reuse accounting | estimated macro |
| B4 joint synthesis | no matching verified NCF integration | unavailable |
| H1 dependent triples | emitted unitary circuit; measurement cleanup is a macro | emitted in unitary profile |

HWP uses a conservative workspace bound: input parities remain in dedicated
clean registers and binary weight output/scratch receives a separate register.
This may overstate workspace, but does not understate it.

## Initial hypothesis choice

H1 was selected because the smallest witness is exact and locally testable:

```text
a + b + (a XOR b) = 2(a OR b).
```

The first detector chooses lexicographically ordered, disjoint triples with
equal exact angle IDs and unit coefficients.  This is an elementary identity,
not a novelty claim.  The mechanism is falsified as a useful direction if its
complete unitary implementation fails to beat strong baselines on independent
nontrivial instances at generic angles.

## Measurement and catalyst policy

Both `unitary_clifford_t` and `measurement_assisted_clifford_t` are separate
profiles.  A 7-T ancilla-free Toffoli is used for emitted unitary circuits.
Temporary logical AND and HWP measurement cleanup use named published macro
costs and cause `accounting_status=estimated_macro`.

Catalyst qubits count toward workspace.  Preparation rotations and their
errors are explicit.  For `R` uses, the prototype charges catalyst preparation
error once and application synthesis error `R` times under a conservative
operator-norm telescoping bound.  It reports preparation depth, application
depth, and composed depth; it never amortizes depth.

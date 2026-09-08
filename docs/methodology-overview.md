# Methodology Overview

## Current algorithm and tradeoff

The target is a block of equal-angle parity phases

```text
U(theta)|x> = exp(i theta sum_j p_j(x)) |x>,
p_j(x) = parity(a_j & x).
```

The basic implementation treats every predicate independently: compute one
parity with CNOTs, apply `P(theta)`, and uncompute the parity.  Therefore, three
predicates normally require three synthesized rotations.

The current candidate looks for a dependent triple of masks

```text
A, B, C, where C = A XOR B.
```

For their Boolean values `a`, `b`, and `a XOR b`, it uses the exact identity

```text
a + b + (a XOR b) = 2(a OR b).
```

The compiler consequently replaces three `P(theta)` rotations with one
`P(2 theta)` rotation:

1. Compute parities `a` and `b` into two clean work qubits.
2. Compute `a OR b` into a third clean work qubit.
3. Apply `P(2 theta)` to the OR result.
4. Reverse the computation and return all work qubits to zero.

The unitary implementation trades two arbitrary rotations for two Toffolis,
three clean work qubits, and additional Clifford gates.  Each Toffoli is
currently emitted with a 7-T decomposition.  This can reduce T-count when
generic rotation synthesis is more expensive than the added 14 T gates.

The tradeoff is not always favorable:

- Special Clifford+T angles can make the original rotations cheap.
- A block without an eligible equal-angle, unit-coefficient triple is left
  unchanged.
- Overlapping triples are selected by a deterministic disjoint greedy rule;
  the current implementation does not claim globally optimal selection.
- Added computation can increase scheduled T-depth even when T-count falls.
- The transformation requires three extra logical qubits when used.

Ordinary Hamming-weight phasing provides the main comparison.  It trades a
large batch of rotations for weight-computation arithmetic and fewer rotations.
With limited workspace, the current evaluation divides terms into balanced
batches.  Catalyzed HWP further trades rotation synthesis for catalyst
preparation, storage, and arithmetic.  These HWP methods currently use verified
ideal semantics and published resource formulas, but their arithmetic circuits
are not yet fully emitted.

## Evaluation pipeline

```text
frozen manifest -> acquisition -> canonical IR -> structure profile
                -> compile methods -> semantic verification
                -> Clifford+T lowering -> resource scheduling
                -> result validation -> comparison report
```

1. **Freeze inputs.** Each case records its source, selection rule, revision,
   checksum, generator parameters, and seed before candidate evaluation.
2. **Acquire data.** Public files are downloaded without overwriting existing
   data and accepted only when their SHA-256 checksums match the manifest.
3. **Build the canonical IR.** The loader preserves term IDs, parity masks,
   multiplicities, exact angle-class IDs, coefficients, block boundaries, and
   qubit order.
4. **Profile structure.** The profiler measures term count, unique parities,
   duplicate multiplicities, binary rank, dependency witnesses, dependent
   triples, support sizes, and graph properties such as degree and triangles.
5. **Compile comparable methods.** Every method receives the same program,
   total synthesis-error budget, workspace budget, and gate-model profile.
6. **Verify semantics.** For small cases, every basis input is checked for the
   correct phase, unchanged data, and zero returned workspace.  A separate
   coherent-state check is used when the total state vector is small enough.
7. **Lower and count resources.** Generic rotations are synthesized with
   `pygridsynth==2.0.0`; special angles are exact.  Each synthesized matrix is
   checked in operator norm.  A common dependency scheduler reports T-count,
   T-depth, workspace, total qubits, Clifford count when known, measurements,
   and adaptive rounds.
8. **Store and validate results.** One JSON row is written per case and method
   setting.  Missing, infeasible, unavailable, and failed results remain
   explicit.  Circuit hashes and error bounds are rechecked before reporting.

## Benchmarks

The smoke suite contains three deterministic synthetic cases: a triangle, a
four-vertex path, and the smallest dependent-parity witness `{1, 2, 3}`.  It is
used for fast semantic and CLI checks.

The frozen pilot manifest contains 13 cases:

- Three checksum-pinned public unweighted MaxCut graphs from QED-C, with 4, 6,
  and 8 vertices.
- Eight synthetic diagnostics covering paths, cycles, stars, triangles,
  cliques, bicliques, duplicate parities, and dependent parity sets.
- Two negative controls with unequal weights or irregular independent masks.

The initial decision run uses every pilot case with `theta=0.173`, total
operator-norm synthesis error `1e-4`, eight extra logical qubits, and the
unitary Clifford+T profile.  The full planned grid additionally contains three
angles, two error budgets, workspace budgets `{0, 8, 32}`, and separate unitary
and measurement-assisted profiles.

## Methods compared

| Method | Description | Current evidence level |
| --- | --- | --- |
| `independent` | Compute, phase, and uncompute each unique parity | Fully emitted |
| `shared_parity` | Reuse CNOT parity-network state through a greedy parity walk | Fully emitted |
| `hwp` | Compute parity inputs, phase their Hamming weight, and clean up | Ideal semantics plus resource macros |
| `catalyzed_hwp` | HWP with reusable phase-gradient catalysts | Ideal semantics plus resource macros |
| `dependent_triples` | Replace eligible triples by the OR construction above | Fully emitted in the unitary profile |
| `joint_synthesis` | Intended NCF-compatible comparison | Unavailable; not ranked |

The initial report compares emitted methods separately from macro-estimated
methods.  Its results are evidence for continuing the investigation, not a
claim of novelty or final superiority.


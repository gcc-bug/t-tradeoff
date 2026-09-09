# Semantic Contract

For computational-basis input `x`, term `j` stores an integer bit mask `a_j`,
an affine offset `b_j`, an exact integer coefficient `c_j`, and an exact angle
class ID.  Its predicate is

```text
p_j(x) = parity(a_j & x) XOR b_j.
```

The target phase is the sum of `c_j * theta_j * p_j(x)` over terms.  Sums are
integer sums, never XOR sums.  Duplicate terms remain distinct in the IR; a
compiler may combine them exactly and records that action in its trace.

For a MaxCut edge `(u,v)`, the mask is `(1 << u) | (1 << v)` and the predicate
is `x_u XOR x_v`.  The package applies `P(theta)` to that predicate.  To express
standard `exp(-i gamma C)`, bind `theta=-gamma`; no hidden factor of two is
introduced.

Successful small candidates are checked on every data basis state.  The
verifier requires unchanged data, all-zero returned workspace, and the target
complex phase.  Because every ideal operation is either a basis permutation or
a diagonal phase, this exhaustive check establishes action on arbitrary
superpositions.  A separate state-vector test propagates a random coherent
state for small total register sizes.

After lowering, a separate verifier implements only the emitted one- and
two-qubit matrices and does not reuse the ideal operation interpreter. For
small circuits it builds the clean-input isometry and compares it with the
target isometry in spectral norm, including workspace leakage and global
phase. A memory estimate is checked before allocation. Larger circuits receive
explicit compositional scope based on deterministic gate replay, validated
primitive decompositions, exact transformation certificates, and summed local
synthesis error.

Legacy HWP macros are reversible XOR embeddings of the binary Hamming weight,
followed by exact bit-weighted phases and inverse cleanup. This proves the
compiler transformation, not the published macro's gate decomposition. Their
verification status remains ideal-macro-only.

The primary `hwp_adder_unitary` construction emits staged compressor arithmetic
on materialized parity wires, phases the surviving binary-weight wires, and
reverses arithmetic and parity preparation. The old `hwp_emitted` ANF path is
retained only as a small correctness reference. Both emitted paths must pass
clean-workspace and lowered-circuit verification.

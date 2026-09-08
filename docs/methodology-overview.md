# Methodology Overview

## Current algorithm and its tradeoff

The compiler targets diagonal parity phases:

    U|x> = exp(i sum_j theta_j c_j p_j(x)) |x>
    p_j(x) = parity(a_j & x) XOR b_j

All methods first use the same block-local preprocessing. Constants become a
global phase, affine complements are normalized, exact duplicates are merged,
cancellations are removed, and terms are grouped only when block, angle ID,
and integer coefficient match.

The raw candidate looks for a compatible mask triple A, B, and A XOR B. If
their Boolean values are a, b, and a XOR b, then:

    a + b + (a XOR b) = 2(a OR b)

It computes a and b into two clean qubits, computes a OR b into a third,
applies one phase with angle 2 theta c, and uncomputes everything. The
tradeoff is two fewer arbitrary rotations in exchange for two Toffolis,
additional Clifford gates, and three clean work qubits. The raw compiler keeps
the rewrite even when this loses. The selected compiler lowers the raw,
independent, and shared-parity alternatives under the same total error budget
and chooses by the declared objective with a deterministic tie-break.

Ordinary Hamming-weight phasing is evaluated in three explicit forms:

- hwp_emitted computes binary weight with an emitted, out-of-place ANF
  reference circuit and searches legal batch caps using full lowering.
- hwp_emitted_triple_grouped applies that generic arithmetic to exactly the
  raw candidate's triple groups, isolating the grouping effect.
- hwp_dependency_simplified simplifies the same triple's weight bits. Its
  low bit is constant zero and its high bit is a OR b.

The last form emits the same circuit as the raw triple rewrite. The repaired
pilot confirms identical operation streams on all 13 cases. Therefore the
current rule is an HWP specialization, not a surviving new mechanism. It is
retained as a regression and teaching case.

## Evaluation pipeline

    frozen manifest
      -> checksum-checked acquisition or deterministic generation
      -> canonical parity-phase IR
      -> shared preprocessing and structural profile
      -> explicit compiler variants
      -> ideal semantic verification
      -> common Clifford+T lowering and rotation synthesis
      -> independent emitted-gate verification
      -> dependency scheduling and resource accounting
      -> artifact replay and matched, stratified reporting

Each method receives the same target, exact angle binding, total operator-norm
synthesis budget, workspace limit, gate model, reuse count, and objective.
Generic rotations use pygridsynth 2.0.0; exact multiples of pi/4 use exact
Clifford+T gates.

For small emitted circuits, the independent verifier constructs the complete
clean-input isometry and compares it with the target using spectral norm. It
uses its own one- and two-qubit matrices rather than the ideal-operation
interpreter. A memory preflight prevents accidental exponential allocation.
Larger circuits receive explicitly labeled compositional evidence: validated
primitive streams, replayed lowering, exact transformation certificates, and
the sum of independently recomputed rotation errors. Macro events never count
as emitted verification.

Every successful schema-v2 row stores the program, candidate, rotations,
lowered events, global phase, verification evidence, resource record, and all
selection alternatives. Verification reconstructs these objects and recomputes
the target identity, ideal semantics, lowering, synthesis bound, gate-level
evidence, and resources. Hashes detect accidental changes; replay detects
semantically invalid changes even if a hash is updated.

## Benchmarks and reporting

The repaired development pilot keeps the previously frozen 13 cases and
setting: one generic angle (0.173), total operator-norm budget 1e-4, eight
work qubits, and the unitary Clifford+T model.

| Stratum | Cases | Role |
| --- | ---: | --- |
| Public | 3 checksum-pinned QED-C MaxCut instances | Limited public development evidence |
| Synthetic diagnostic | 8 predeclared graph and parity cases | Mechanism and failure-regime diagnosis |
| Negative control | 2 weighted or irregular cases | Confirm no manufactured applicability |

Reports show absolute T-count, scheduled logical T-depth, peak workspace,
error bound, selected construction, and verification scope per instance.
Wins, ties, and regressions use matched populations for each named baseline and
for the best eligible strong baseline. Legacy macro estimates are displayed
separately and cannot enter primary rankings. The emitted HWP implementation is
a correctness reference, not yet a competitive reproduction of published
in-place or measurement-assisted HWP.

# HWP Implementation Audit

## Implemented emitted reference

The hwp_emitted variant materializes each parity predicate, computes binary
population count into a separate clean output register, phases output bit j by
2^j times the compatible group angle and coefficient, and reverses arithmetic
and parity preparation.

Output bit j is emitted as the XOR of all input monomials of degree 2^j. This
is the elementary-symmetric-polynomial characterization of binary Hamming
weight over GF(2), following Lucas' theorem. Multi-controlled X gates are
decomposed into explicit Toffolis using clean scratch, and every Toffoli is
then lowered into the shared exact 7-T unitary decomposition. Tests exhaust
all input values for batch sizes one through eight and check computation,
scratch restoration, and inversion.

For batch size m, this reference uses:

    m parity qubits
    + m.bit_length() weight-output qubits
    + max(0, 2^floor(log2(m)) - 2) clean monomial scratch qubits

This is an implementation upper bound. It is not an ancilla lower bound.

## Prior construction comparison

The ordinary-HWP source tracked for this repository is Kivlichan et al.,
arXiv:1902.10673v4, Section 2.1 and Appendix A. Its adders, in-place layout,
and measurement-assisted cleanup do not match this ANF reference. Therefore
its published formulas are not used to assign counts or depth to the emitted
circuit. The older formula implementation is retained under the explicit
hwp_macro_legacy method and excluded from primary ranking.

The catalytic source tracked is Kan-Symons, arXiv:2411.02160v2. Its phase
gradient, catalyst lifecycle, and measured cleanup are not emitted here.
Catalytic counts remain unverified estimates and are absent from the repaired
unitary pilot.

The implemented reference is expected to be weaker than a production in-place
or measurement-assisted HWP construction. It is sufficient for validating
semantics and testing the structural overlap, but not for claiming superiority
over the strongest published ordinary-HWP baseline.

## Structural ablation

The generic triple-grouped variant applies this arithmetic to the exact
disjoint triples chosen by the raw candidate. The dependency-simplified
variant observes that the triple weight has truth table [0, 2, 2, 2], so its
low bit is constant and its only nonconstant bit is a OR b.

That simplification emits exactly the raw candidate circuit. This establishes
that the present triple identity is subsumed by simplified Hamming-weight
phasing. It does not establish novelty, optimality, or a broader compiler
advantage.

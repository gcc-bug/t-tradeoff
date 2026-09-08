# Hypothesis Card: Dependent Parity Triples

## Observation

For Boolean values `a,b`, the three predicates `a`, `b`, and `a XOR b` have
integer weight zero when both are zero and weight two otherwise.  Therefore

```text
P(theta)^a P(theta)^b P(theta)^(a XOR b) = P(2 theta)^(a OR b).
```

This applies to any three nonzero parity masks whose XOR is zero, provided
their exact angle class and unit coefficient agree.

## Nearest prior result

Ordinary Hamming-weight phasing computes the weight of a same-angle batch and
phases its binary representation.  Computed phasing more generally permits a
function to be computed and phased.  The identity here is an HWP specialization
that avoids materializing the third predicate and a generic popcount network.
No novelty is asserted; precise prior-art overlap still needs a targeted check.

## Proposed difference

The emitted unitary witness computes two parity values, computes their OR into
a third clean qubit, applies one `P(2 theta)`, and reverses all work.  OR uses a
Toffoli plus two CNOTs in each direction.  Complete cost is therefore one
generic rotation, two unitary Toffolis, parity computation, and cleanup.

## Smallest witness

Two data qubits with masks `{1,2,3}`.  Exhaustive and coherent-state tests cover
all four data inputs and three returned workspace qubits.

## Predicted regimes

Favorable: generic angles at strict precision when two avoided rotation
syntheses cost more than two Toffolis, and blocks contain disjoint dependent
triples.  Graph triangles are one source of such triples.

Unfavorable: special Clifford angles; sparse triangle-free graphs; overlapping
triples with low edge coverage; unequal coefficients or angle IDs; and strong
HWP/joint synthesis that already derives an equivalent reduced function.

## Falsification test

Compare the complete emitted unitary circuit against emitted independent and
shared-parity baselines and a strengthened emitted HWP baseline under equal
total error and workspace.  Stop this mechanism if no advantage survives on
more than one independently selected nontrivial public case or if direct prior
art already subsumes the detector and construction.


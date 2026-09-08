# M3-W Structural Decision

Date: 2026-09-08

Decision: current rule subsumed; M3-W not achieved.

The raw rule rewrites compatible predicates using
`a + b + (a XOR b) = 2(a OR b)`. The corresponding three-predicate Hamming
weight has low bit zero and high bit `a OR b`. The dependency-simplified HWP
compiler therefore emits exactly the raw rewrite.

In the repaired development pilot, the two variants have the same emitted
operation stream on all 13 cases. The selected candidate records no T-count
advantage over this overlap baseline:

- Public: 0 wins and 3 ties against dependency-simplified HWP.
- Synthetic diagnostics: 0 wins, 8 ties against simplified; 2 regressions
  against the best strong baseline because generic HWP was better.
- Negative controls: 0 wins, 2 ties against simplified.

The earlier wins against independent and shared-parity synthesis remain real
resource differences for those named basic references, but do not isolate a
new mechanism beyond Hamming-weight phasing. The emitted generic HWP reference
is also not strong enough to support a broad prior-work performance claim.

The current triple rule should remain as a correctness, selection, and
regression test. Further work needs a new bounded hypothesis whose advantage
survives dependency-simplified HWP and a competitive implementation of the
relevant prior construction. Infrastructure completion is M2-R evidence, not
M3-W novelty evidence.

# Resource and Error Model

## Gate profiles

`unitary_clifford_t` permits no measurement.  Toffoli is lowered with the
standard exact ancilla-free 7-T decomposition.  Its reported T-depth comes
from scheduling the emitted dependency stream; it is not claimed minimal.

`measurement_assisted_clifford_t` permits measurement and feed-forward.
Temporary logical AND computation is charged 4 T and its measurement-assisted
uncompute is charged zero T plus one measurement/adaptive dependency.  Unknown
macro Clifford counts are reported as `null`, not zero.

`hwp_adder_unitary` is the primary ordinary-HWP path. For a batch of size `n`,
it materializes `n` parity inputs and uses `n - popcount(n)` clean carry wires.
Forward and reverse arithmetic each contain `n - popcount(n)` Toffolis, all
lowered by the shared exact 7-T decomposition. This unitary cleanup deliberately
does not claim the lower cost of measurement-assisted uncomputation.

`hwp_emitted` is the old out-of-place ANF population-count correctness
reference. It is capped at eight inputs and excluded from default rankings.
`hwp_macro_legacy` retains the older formula interpretation under an explicit,
unranked label.

Catalyzed HWP estimates add the Kan-Symons generalized phase-gradient Toffoli count,
one residual synthesized rotation per nontrivial batch, catalyst registers,
and all catalyst preparation rotations. These channels and formulas have not
been independently emitted and remain excluded from primary rankings. Reuse
count is never inferred from shots or parameter updates.

## Scheduler

Each Clifford operation propagates the maximum dependency level of all touched
qubits without increasing it.  Each `T` or `T-dagger` operation increments the
level. Macro depth values are historical estimates and are not ranked.
Measurement-to-correction rounds remain causal.

## Error allocation

Generic rotation synthesis uses one total operator-norm budget per method.
For noncatalytic methods the budget is divided over the method's actual generic
rotations.  For a catalytic method with both preparation and application
rotations, half is assigned to preparation and half across all declared uses.
The stored bound is the sum of measured local operator-norm errors.  Exact
Clifford+T angles contribute zero.  Catalyst-state approximation and
application synthesis remain separate in circuit artifacts.

The model does not include Trotter error, input coefficient rounding, physical
runtime, factory throughput, routing, or code distance.

# Resource and Error Model

## Gate profiles

`unitary_clifford_t` permits no measurement.  Toffoli is lowered with the
standard exact ancilla-free 7-T decomposition.  Its reported T-depth comes
from scheduling the emitted dependency stream; it is not claimed minimal.

`measurement_assisted_clifford_t` permits measurement and feed-forward.
Temporary logical AND computation is charged 4 T and its measurement-assisted
uncompute is charged zero T plus one measurement/adaptive dependency.  Unknown
macro Clifford counts are reported as `null`, not zero.

Ordinary HWP uses the published count `M - popcount(M)` half/full adders for an
`M`-predicate batch.  Measurement-assisted cleanup is charged separately.
The unitary profile conservatively lowers both compute and inverse at 7 T per
adder.  HWP circuit internals are not yet emitted, so both profiles remain
`estimated_macro`.

Catalyzed HWP adds the Kan-Symons generalized phase-gradient Toffoli count,
one residual synthesized rotation per nontrivial batch, catalyst registers,
and all catalyst preparation rotations.  Generalized phase-gradient Toffolis
are conservatively charged at 7 T each.  Reuse count is never inferred from
shots or parameter updates.

## Scheduler

Each Clifford operation propagates the maximum dependency level of all touched
qubits without increasing it.  Each `T` or `T-dagger` operation increments the
level.  Macro depth increments are documented upper-bound estimates and are
visibly labeled.  Measurement-to-correction rounds remain causal.

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


# Resource and Error Model

## Gate profiles

`unitary_clifford_t` permits no measurement.  Toffoli is lowered with the
standard exact ancilla-free 7-T decomposition.  Its reported T-depth comes
from scheduling the emitted dependency stream; it is not claimed minimal.

`measurement_assisted_clifford_t` remains a declared model boundary, but no
active HWP implementation emits measurement/feed-forward operations. It is not
ranked in the schema-v3 adaptive study.

`hwp_adder_unitary` is the primary ordinary-HWP path. For a batch of size `n`,
it materializes `n` parity inputs and uses `n - popcount(n)` clean carry wires.
Forward and reverse arithmetic each contain `n - popcount(n)` Toffolis, all
lowered by the shared exact 7-T decomposition. This unitary cleanup deliberately
does not claim the lower cost of measurement-assisted uncomputation.

The old ANF, macro, and catalytic estimate paths are not active code. Their
assumptions are retained in the historical reports and HWP/prior-work audits.

## Scheduler

Each Clifford operation propagates the maximum dependency level of all touched
qubits without increasing it. Each `T` or `T-dagger` increments the level. A
reverse pass records T-critical events and slack. Peak additional logical
qubits comes from wires actually allocated in the lowered circuit, including
optimizer outputs, rather than a candidate's declared maximum alone.

## Error allocation

Generic rotation synthesis uses one total operator-norm budget per complete
circuit, divided over its actual generic rotations. The stored bound is the sum
of measured local operator-norm errors; exact Clifford+T angles contribute zero.
External actions are exact rewrites of that already-synthesized stream and do
not consume a second approximation budget.

The model does not include Trotter error, input coefficient rounding, physical
runtime, factory throughput, routing, or code distance.

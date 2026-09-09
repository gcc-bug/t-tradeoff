# Review Guide

## 1. Input Meaning

A `PhaseProgram` represents diagonal phases whose predicates are affine parity
functions. See `PhaseProgram.phase_radians` in
[`ir.py`](../src/collective_phase/ir.py) and the single common normalization
pass, `preprocess`, in
[`preprocessing.py`](../src/collective_phase/preprocessing.py).

## 2. Implemented Constructions And Backends

The default configuration uses three emitted constructions:

- `compile_independent`: compute, phase, and uncompute each normalized parity;
- `compile_shared_parity`: reuse an anchor parity walk to reduce CNOT changes;
- `compile_hwp_adder_unitary`: materialize equal-angle parities, compress their
  Hamming weight with staged adders, phase the weight bits, and reverse all work.

Their entry points are exported from
[`baselines/__init__.py`](../src/collective_phase/baselines/__init__.py). The
ANF, dependent-triple, catalytic-estimate, and legacy-macro implementations
have been removed from the active package and remain available in Git history.

Exact post-synthesis adapters are in
[`adapters/`](../src/collective_phase/adapters). PyZX exposes basic
optimization, TODD/full optimization, and ZX reduction/extraction. The
optional Feynman subprocess adapter exposes only passes advertised by the
resolved executable and requires both Feynman's verification and an independent
PyZX equivalence reduction.

## 3. Checking And Counting

`verify_candidate` checks the ideal construction and clean workspace.
`verify_lowered_circuit` independently validates rotation matrices, the exact
Toffoli decomposition, event-to-primitive binding, global phases, and the
whole-circuit error allocation before returning a compositional certificate.
`estimate_resources` schedules the actual event dependencies; it does not add
stage depths as if all gates were serial.

Relevant functions are in
[`verification/core.py`](../src/collective_phase/verification/core.py),
[`verification/lowered.py`](../src/collective_phase/verification/lowered.py),
and [`resources.py`](../src/collective_phase/resources.py).

## 4. Objective And Search

[`selection.py`](../src/collective_phase/selection.py) implements constrained
single-metric objectives and a weighted normalized balance with fixed positive
reference scales. Ancilla-first selection requires explicit T-count and T-depth
limits. [`search.py`](../src/collective_phase/search.py) shares verified seeds
across policies, ranks actions from schedule and circuit evidence, enforces call
and time budgets, and permits at most one construction seed followed by one
backend action.

## 5. Trace One Example

For `independent_equal_angle`, the manifest creates four one-qubit predicates
at angle `0.173`. The runner sends the same normalized program, total error,
workspace budget, and gate model to all three constructors. The HWP generator
emits batch limits 1-4 and lowers each with its actual rotation count. The
selection code keeps nondominated `(T, T-depth, ancilla)` tuples and chooses
under the configured T-count policy. The report row splits total T into
arithmetic and synthesized-rotation components.

In `hwp_joint_optimization_witness`, the fixed balance objective scores the
direct seed `(200,50,0)` at `0.9125`. The HWP cap-4 seed is temporarily worse at
`(190,73,7)`, score `0.917`, but verified PyZX extraction reaches
`(176,114,7)`, score `0.86425`. Fixed order reaches the same endpoint, so this
is evidence for the enabling sequence rather than adaptive-policy superiority.

Follow the execution through `run_experiments` in
[`experiments.py`](../src/collective_phase/experiments.py), `run_policy` in
[`search.py`](../src/collective_phase/search.py), and
`render_comparison_report` in
[`reporting.py`](../src/collective_phase/reporting.py).

## 6. Unsupported Claims

The workbench does not claim a novel construction, global optimum, or adaptive
advantage. NCF has no located public implementation; Trasyn would introduce a
second approximate synthesis stage; the current relational Feynman passes were
not built. The default HWP is a unitary adaptation, not the cheaper measured
cleanup from the source. Public QED-C and synthetic cases are development data.

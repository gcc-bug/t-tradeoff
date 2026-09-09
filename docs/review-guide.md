# Review Guide

## 1. Input Meaning

A `PhaseProgram` represents diagonal phases whose predicates are affine parity
functions. See `PhaseProgram.phase_radians` in
[`ir.py`](../src/collective_phase/ir.py) and the single common normalization
pass, `preprocess`, in
[`preprocessing.py`](../src/collective_phase/preprocessing.py).

## 2. Implemented Constructions

The default configuration uses three emitted constructions:

- `compile_independent`: compute, phase, and uncompute each normalized parity;
- `compile_shared_parity`: reuse an anchor parity walk to reduce CNOT changes;
- `compile_hwp_adder_unitary`: materialize equal-angle parities, compress their
  Hamming weight with staged adders, phase the weight bits, and reverse all work.

Their entry points are exported from
[`baselines/__init__.py`](../src/collective_phase/baselines/__init__.py). The
ANF and dependent-triple implementations are retained but absent from
[`configs/default-study.yaml`](../configs/default-study.yaml).

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

## 4. Trace One Example

For `independent_equal_angle`, the manifest creates four one-qubit predicates
at angle `0.173`. The runner sends the same normalized program, total error,
workspace budget, and gate model to all three constructors. The HWP generator
emits batch limits 1-4 and lowers each with its actual rotation count. The
selection code keeps nondominated `(T, T-depth, ancilla)` tuples and chooses
under the configured T-count policy. The report row splits total T into
arithmetic and synthesized-rotation components.

Follow the execution through `_execute_method` in
[`experiments.py`](../src/collective_phase/experiments.py),
`select_lowered_candidate` in
[`selection.py`](../src/collective_phase/selection.py), and
`render_comparison_report` in
[`reporting.py`](../src/collective_phase/reporting.py).

## 5. Unsupported Claims

The workbench does not claim that the selected construction is novel or
globally optimal. The default HWP is a unitary adaptation, not the cheaper
measured cleanup from the source. Catalytic HWP has not passed catalyst-state,
channel, and repeated-use verification. The public QED-C cases are development
data. The current study can identify a cost crossover or limitation; it cannot
support broad benchmark or prior-work-coverage claims.

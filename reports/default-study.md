# Construction Tradeoff Study

Results: `results/raw/default-study`

This fixed study compares named circuit constructions under one common parity-phase target, lowering backend, and whole-circuit operator-norm error budget. Compilation time is diagnostic only.

Declared selection policy: `t_count`; hard limits: ancilla=8.

## Status

- `success`: 21

## Construction Results

Arithmetic T is the T cost outside synthesized rotations. Rotation T includes application rotations and any resource-state preparation.

| Case | Method | Variant | Generic rotations | Arithmetic T | Rotation T | Total T | T-depth | Peak ancillas | Error | Verification scope | Evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| dependent_triple | hwp_adder_unitary | adder_compressor_unitary_cap_3 | 2 | 14 | 94 | 108 | 56 | 4 | 4.235113079334664e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| dependent_triple | independent | normalized_independent | 3 | 0 | 150 | 150 | 100 | 0 | 4.6867877680177285e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| dependent_triple | shared_parity | normalized_greedy_anchor_walk | 3 | 0 | 150 | 150 | 150 | 0 | 4.6867877680177285e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| independent_equal_angle | hwp_adder_unitary | adder_compressor_unitary_cap_4 | 3 | 42 | 148 | 190 | 73 | 7 | 4.477652754803408e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| independent_equal_angle | independent | normalized_independent | 4 | 0 | 200 | 200 | 50 | 0 | 3.653253462600486e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| independent_equal_angle | shared_parity | normalized_greedy_anchor_walk | 4 | 0 | 200 | 200 | 50 | 0 | 3.653253462600486e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| overlapping_dependencies | hwp_adder_unitary | adder_compressor_unitary_cap_3 | 4 | 28 | 200 | 228 | 116 | 4 | 4.1363520828444104e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| overlapping_dependencies | independent | normalized_independent | 6 | 0 | 312 | 312 | 208 | 0 | 3.556820104144808e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| overlapping_dependencies | shared_parity | normalized_greedy_anchor_walk | 6 | 0 | 312 | 312 | 260 | 0 | 3.556820104144808e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| weighted_triangle_free | hwp_adder_unitary | adder_compressor_unitary_cap_1 | 5 | 0 | 254 | 254 | 254 | 0 | 4.006872019389769e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| weighted_triangle_free | independent | normalized_independent | 5 | 0 | 254 | 254 | 254 | 0 | 4.006872019389769e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| weighted_triangle_free | shared_parity | normalized_greedy_anchor_walk | 5 | 0 | 254 | 254 | 254 | 0 | 4.006872019389769e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_004_003_000 | hwp_adder_unitary | adder_compressor_unitary_cap_3 | 4 | 28 | 200 | 228 | 116 | 4 | 4.1363520828444104e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| qedc_mc_004_003_000 | independent | normalized_independent | 6 | 0 | 312 | 312 | 260 | 0 | 3.556820104144808e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_004_003_000 | shared_parity | normalized_greedy_anchor_walk | 6 | 0 | 312 | 312 | 260 | 0 | 3.556820104144808e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_006_003_000 | hwp_adder_unitary | adder_compressor_unitary_cap_3 | 6 | 42 | 312 | 354 | 180 | 4 | 3.6313455858807336e-05 | clean_input_isometry_spectral_norm | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| qedc_mc_006_003_000 | independent | normalized_independent | 9 | 0 | 468 | 468 | 260 | 0 | 3.600911231375151e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_006_003_000 | shared_parity | normalized_greedy_anchor_walk | 9 | 0 | 468 | 468 | 260 | 0 | 3.600911231375151e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_008_003_000 | hwp_adder_unitary | adder_compressor_unitary_cap_3 | 8 | 56 | 416 | 472 | 240 | 4 | 4.841794114507645e-05 | ideal_semantics_primitive_matrices_event_binding_and_error_budget | audited_prior_construction / unitary_adaptation_emitted_and_verified |
| qedc_mc_008_003_000 | independent | normalized_independent | 12 | 0 | 624 | 624 | 260 | 0 | 4.801214975166868e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |
| qedc_mc_008_003_000 | shared_parity | normalized_greedy_anchor_walk | 12 | 0 | 624 | 624 | 260 | 0 | 4.801214975166868e-05 | clean_input_isometry_spectral_norm | basic_reference / emitted_and_verified |

## Pareto And Selection

The Pareto set uses `(T, T-depth, ancillas)` for every validated default-study construction. Selection then applies the declared hard limits and objective; limits are never relaxed.

Each policy below selects among the same evaluated circuits. The configuration declares `t_count`; the other columns expose how preference alone changes the result.

| Case | Pareto alternatives | T-count choice | T-depth choice | Ancilla choice |
| --- | --- | --- | --- | --- |
| dependent_triple | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_3, independent:normalized_independent | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| independent_equal_angle | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_4, independent:normalized_independent, shared_parity:normalized_greedy_anchor_walk | hwp_adder_unitary:adder_compressor_unitary_cap_4 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| overlapping_dependencies | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_2, hwp_adder_unitary:adder_compressor_unitary_cap_3, hwp_adder_unitary:adder_compressor_unitary_cap_4, hwp_adder_unitary:adder_compressor_unitary_cap_5, hwp_adder_unitary:adder_compressor_unitary_cap_6, independent:normalized_independent | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| qedc_mc_004_003_000 | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_2, hwp_adder_unitary:adder_compressor_unitary_cap_3, hwp_adder_unitary:adder_compressor_unitary_cap_4, hwp_adder_unitary:adder_compressor_unitary_cap_5, hwp_adder_unitary:adder_compressor_unitary_cap_6, independent:normalized_independent, shared_parity:normalized_greedy_anchor_walk | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| qedc_mc_006_003_000 | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_3, hwp_adder_unitary:adder_compressor_unitary_cap_4, hwp_adder_unitary:adder_compressor_unitary_cap_5, hwp_adder_unitary:adder_compressor_unitary_cap_6, hwp_adder_unitary:adder_compressor_unitary_cap_7, hwp_adder_unitary:adder_compressor_unitary_cap_8, independent:normalized_independent, shared_parity:normalized_greedy_anchor_walk | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_5 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| qedc_mc_008_003_000 | hwp_adder_unitary:adder_compressor_unitary_cap_1, hwp_adder_unitary:adder_compressor_unitary_cap_3, hwp_adder_unitary:adder_compressor_unitary_cap_4, hwp_adder_unitary:adder_compressor_unitary_cap_5, hwp_adder_unitary:adder_compressor_unitary_cap_6, hwp_adder_unitary:adder_compressor_unitary_cap_7, hwp_adder_unitary:adder_compressor_unitary_cap_8, independent:normalized_independent, shared_parity:normalized_greedy_anchor_walk | hwp_adder_unitary:adder_compressor_unitary_cap_3 | hwp_adder_unitary:adder_compressor_unitary_cap_4 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |
| weighted_triangle_free | hwp_adder_unitary:adder_compressor_unitary_cap_1, independent:normalized_independent, shared_parity:normalized_greedy_anchor_walk | hwp_adder_unitary:adder_compressor_unitary_cap_1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 | hwp_adder_unitary:adder_compressor_unitary_cap_1 |

## Interpretation

Across the selected rows, arithmetic contributes 210 T gates and rotation synthesis contributes 1624; rotation synthesis is the larger reported component.

On `independent_equal_angle`, HWP changes T-count from 200 to 190, T-depth from 50 to 73, and peak ancillas from 0 to 7. Thus the T-count choice is not the T-depth or ancilla choice.

On `weighted_triangle_free`, distinct coefficients prevent a multi-term equal-angle group. The HWP constructor records a direct fallback, so its zero-workspace row ties the direct references instead of demonstrating HWP applicability.

An `adder_compressor_unitary_cap_1` choice is the HWP generator's zero-workspace direct fallback. Ancilla-first selections with that label therefore use the direct circuit, not collective arithmetic.

Changing the objective does not generate another circuit. The policy columns select only among the evaluated rows; each HWP artifact also retains its evaluated batch variants and internal Pareto labels.

The ordinary-HWP row is a unitary adaptation of the cited staged-adder construction. Reversing its arithmetic doubles the forward Toffoli cost relative to measurement-assisted cleanup. Measured and catalytic methods are unavailable here because their channel and resource-state obligations have not been implemented.

The dependent-triple rule and the ANF popcount implementation are optional diagnostics, not default competitors. No novelty claim follows from selecting the cheapest existing circuit.

## Research Decision

This seven-case development study does not establish a recurring algorithmic limitation beyond ordinary HWP's expected equal-angle applicability boundary. The weighted negative control is one boundary example, not evidence for a new optimization mechanism.

The next gated comparison is therefore implementation work rather than a novelty claim: emit and channel-verify the audited Gidney cleanup or Kan-Symons catalytic construction, include complete state preparation over matching repeated uses, and test whether it adds a nondominated point to this same fixed workload. If it does not, the hypothesis that measured or catalytic cleanup changes the observed frontier is falsified.

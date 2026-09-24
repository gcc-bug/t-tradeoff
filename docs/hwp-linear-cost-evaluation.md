# Mixed linear-cost HWP evaluation

The active objective is the user-supplied, fixed exact rational cost
`J = lambda_T*T + lambda_D*D_T + lambda_A*A`, with nonnegative weights not all
zero. Mandatory limits define feasibility only. `D_T` is complete-wave depth;
ordinary emitted depth is reported separately. An `OPTIMAL` scalar result has
equal lower and upper cost bounds (`L = U`) and a verified emitted circuit.
The guarantee is restricted to the existing HWP/direct finite recipe library,
normalized-term precision allocation, two arithmetic orderings, unitary clean
ancillas, and complete-wave scheduling. It is not a claim about arbitrary
equivalent circuits or published measurement-assisted constructions.

The frozen development protocol is in
[`configs/hwp-linear-cost-study.yaml`](../configs/hwp-linear-cost-study.yaml).
It uses native nine and two overlapping-mask inputs, four positive raw-resource
weight vectors, error budget `1e-4`, clean-ancilla cap four, and no depth cap.
Each generic method gets three cold-cache repetitions at three seconds; method
order rotates. The simple method uses interleaved refinement with an
integer-rounded T completion bound. The augmented method additionally enables
partition bounds and progress ordering. Both use zero gap tolerance, scalar
tie handling, the same direct seed, and no target-cost stop. On native nine,
the independent partition solver is also timed. Setup, refinement, failed
exploration, and incumbent verification are charged; imports and serialization
are excluded. Actual overruns are retained.

Separate reference runs compute one finite-family frontier per input, using
the independent native partition solver or generic exact solver as applicable,
and a strong batching reference with direct synthesis included. They each get
at most 60 seconds. Only completed references establish an exact optimum or
completed construction comparator; interrupted results remain labeled
incomplete. Reference points and rotation caches never enter timed searches.
The [study report](../reports/hwp-linear-cost-study.md) compares cost, bounds,
gaps, verified tuples, and completion within each input and weight query.
Matching a reference is an efficiency result when faster; lowering its cost
is a circuit-quality gain only against that declared reference.

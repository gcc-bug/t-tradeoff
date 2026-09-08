# Collective Rotation Compilation: Research Exploration and Implementation Plan

Date: 2026-09-07

Status: exploratory research specification, not a confirmed novel algorithm.

Audience: local Codex implementing a reproducible research prototype.

## 0. Instructions to the implementing agent

Read this document completely before implementation. Inspect the local repository and applicable AGENTS.md instructions. Reuse sound existing code where possible; do not assume that an earlier T-optimization implementation already matches this problem.

The task is to establish whether a structural optimization opportunity exists, then implement the smallest method that exploits it. Do not substitute a generic optimizer portfolio, an ancilla-budget sweep, or a large compiler framework for the research objective.

Proceed through the milestones below. Complete diagnostics and verification before expensive experiments. If evidence invalidates a hypothesis, record the negative result and stop expanding that hypothesis. Do not silently replace the research question with a different application, approximation model, or hardware objective.

Use ordinary local git practices. Preserve existing user changes. Do not push, publish, or contact paper authors without authorization. External tools, paper implementations, and data may be unavailable: report their actual status and keep independent tasks moving. Do not invent successful reproductions.

## 1. Research framing

### 1.1 Problem

Explore compilation of equal-angle commuting Pauli rotations into fault-tolerant Clifford+T circuits. Initially focus on diagonal parity phases, particularly unweighted MaxCut QAOA cost layers and equal-coefficient diagonal blocks from spin-model simulation.

Primary metrics are T-count and T-depth. Peak logical workspace and synthesis error are constraints. Physical execution time, factories, routing, and code-distance optimization are outside the initial scope.

### 1.2 Motivation supported by prior work

- Independently synthesizing every arbitrary rotation can be expensive.
- Hamming-weight phasing (HWP) replaces a batch of equal-angle rotations with weight computation and fewer rotations.
- Catalyzed HWP exchanges further rotation synthesis for arithmetic, catalyst preparation, and reusable workspace.
- Joint small-unitary synthesis exploits other relations among rotations.

These facts motivate investigating collective representations. They do not establish that existing methods neglect a particular structure or that a new framework is needed.

### 1.3 Hypothesis to test

Relations among parity predicates may permit a cheaper implementation of their collective phase than treating each predicate as an independent input to a standard HWP construction.

Seek a result of the form:

> Existing construction X repeatedly computes Y for predicate sets satisfying condition S. An equivalent construction Z removes or simplifies Y. The complete resource advantage survives baseline optimization, and S appears in independently selected benchmark instances.

### 1.4 What does not count as the central contribution

- Enumerating ancilla counts and collecting Pareto points.
- Combining published tools and choosing the best output without a new explanatory principle.
- Applying HWP, batching, phase catalysis, or pebbling as if those were new.
- Showing improvements only on complete graphs, complete bipartite graphs, or planted favorable patterns.
- Reporting fewer rotations without including arithmetic, cleanup, and catalyst costs.
- Claiming that fewer T gates necessarily implies lower T-depth or faster physical execution.

### 1.5 Four questions every milestone must answer

1. Observation: what is directly supported by prior work or measured circuits?
2. Gap: what exact behavior is not handled by the nearest applicable prior method?
3. Verification: which equivalence argument, benchmarks, and baselines support the result?
4. Potential: what extension follows if the observation is valid, and what remains speculative?

## 2. Mathematical contract

### 2.1 Canonical initial target

Let x be an n-bit computational-basis input. Define parity predicates

    p_j(x) = a_j · x XOR b_j

where a_j is a binary mask and b_j is a bit. The initial target is

    F(x) = sum_j p_j(x)              # integer sum, not XOR
    U(theta)|x> = exp(i theta F(x))|x>.

Start with b_j = 0 and equal positive coefficients. Preserve multiplicities. Subsequent support for affine terms or signed integer coefficients must explicitly extend the contract.

Use P(theta) = diag(1, exp(i theta)) as the internal phase convention. Rz(theta) differs from P(theta) by a global phase; store that phase when translating. Global phase can become a relative phase under control, so controlled application is not implicitly supported.

For unweighted MaxCut:

    F_G(x) = sum_(u,v in E) (x_u XOR x_v).

Standard exp(-i gamma C) corresponds to theta = -gamma when C is the cut-value operator. Verify each benchmark generator's sign and factor-of-two convention.

### 2.2 Ancilla semantics

For deterministic clean-workspace implementations, require

    V(|psi> |0...0>) = (U|psi>) |0...0>

for every input state, within the declared synthesis error. Matching only measurement probabilities or only |+> inputs is insufficient.

Catalytic implementations require their stated input resource state and return it ideally. Record catalyst preparation, its approximation error, and assumptions behind repeated use. A catalyst is not a free clean ancilla.

Measurement-assisted implementations must implement the target channel after outcome-dependent corrections and discarding classical outcomes. Prove or verify that outcomes do not leak input information in a way that changes the channel.

### 2.3 Extension to commuting Pauli blocks

A general commuting block may be diagonalized by a Clifford transformation. Preserve Pauli signs, rotation conventions, and the diagonalizing Clifford. Dependent Pauli operators need not become independent single-qubit Z operators; they may remain multi-qubit parities.

Initially use diagonal blocks to avoid making simultaneous diagonalization a prerequisite. Later add general commuting blocks only with verified adapters and complete Clifford overhead accounting.

Never reorder noncommuting product-formula terms merely to enlarge batches. Keep QAOA mixer barriers. Any changed simulation formula is a separate algorithmic approximation outside this initial project.

## 3. Literature audit and baseline provenance

Create docs/prior-work-matrix.md. For each source record title, version/date, exact section or theorem, code URL if verified, implementation availability, gate model, metric definitions, applicable inputs, and overlap with the candidate mechanism.

Seed references:

| Source | Role |
| --- | --- |
| [Ross–Selinger, rotation synthesis](https://arxiv.org/abs/1403.2975) | Independent-rotation baseline; use actual synthesis rather than only asymptotic formulas. |
| [Gidney, Halving the cost of quantum addition](https://arxiv.org/abs/1709.06648) | Temporary logical ANDs, measurement-assisted cleanup, and weight-based rotations. |
| [Kivlichan et al., fault-tolerant simulation](https://arxiv.org/abs/1902.10673) | HWP implementations and reduced-workspace variants. |
| [Campbell, early Hubbard simulation](https://arxiv.org/abs/2012.09238) | Explicit HWP accounting, especially Appendix E. |
| [Kan–Symons, catalyzed HWP](https://arxiv.org/abs/2411.02160) | Essential catalytic and batched baseline. |
| [Gidney–Fowler, phase catalysis](https://arxiv.org/abs/1812.01238) | Catalyst semantics and generalized phase constructions. |
| [Kim, constant-T-depth catalytic rotations](https://arxiv.org/abs/2506.15147) | Important comparison if depth becomes the claimed improvement. |
| [Non-Clifford Fusion](https://arxiv.org/abs/2510.13573) | Joint-synthesis competitor where applicable; verify precision conventions and code availability. |
| [Reversible pebbling](https://arxiv.org/abs/1904.02121) | Prior art for retention and recomputation. |
| [Computed phasing explanation](https://algassert.com/post/1719) | Prior art for computing a function and applying its phase. |
| [Rajakumar et al., graph coupling compilation](https://arxiv.org/abs/2011.08165) | Related graph decomposition with different native primitives. |
| [Dinpazhouh–Hicks, MaxCut compilation](https://arxiv.org/abs/2509.00170) | Related graph-structural bounds; not directly a Clifford+T baseline. |
| [Graph sparsification/decomposition for QAOA](https://arxiv.org/abs/2406.14330) | Related decomposition; distinguish changed objectives and hardware models. |

Check subsequent versions and references before asserting novelty. An unsuccessful search is not evidence of absence. Do not equate all graph-based or Hamming-weight-based papers: explain the exact overlap.

NCF's reported two-qubit setup uses comparatively loose block tolerances; do not transfer published gains to stringent precision without reproduction. Do not mix its single- and two-qubit precision settings.

## 4. Benchmark acquisition and frozen pilot suite

### 4.1 Public sources

- [HamLib paper](https://arxiv.org/abs/2306.13126), [data portal](https://portal.nersc.gov/cfs/m888/dcamps/hamlib/): Hamiltonians, with graph metadata where available, stored in compressed HDF5 files. Contains MaxCut, Ising, Heisenberg, Hubbard, and chemistry families. These are input problems, not fully specified circuits.
- [QED-C application benchmarks](https://github.com/sri-international/qc-app-oriented-benchmarks): MaxCut and Hamiltonian-simulation programs/generators.
- [simcount](https://github.com/njross/simcount): existing Hamiltonian simulation samples, including before/after optimization circuits.
- [Rustiq](https://github.com/qiskit-community/rustiq): Pauli-network synthesis implementation; a compiler component, not an interchangeable replacement for a T synthesizer.
- [NCF benchmark descriptions](https://arxiv.org/html/2510.13573v1): useful comparison cases; exact public artifacts were not confirmed during planning.

Check licenses, archive sizes, and file metadata before bulk acquisition. Download only selected subsets. If public access fails, use seeded generated cases to develop infrastructure, label them synthetic, and leave public-validation status incomplete.

### 4.2 Proposed small pilot

Freeze the selection before evaluating the new candidate:

1. Up to 12 public unweighted MaxCut instances spanning available sizes and sparsity categories. Choose by metadata and fixed ordering/seed, not candidate gains.
2. Up to 8 public spin-model instances with equal-coefficient diagonal blocks, spanning two sizes and multiple geometries/coupling settings where available.
3. A small diagnostic collection: paths, cycles, stars, triangles, cliques, bicliques, duplicate parities, linearly dependent parity sets, and irregular random graphs.
4. Negative controls: weighted instances with distinct coefficients and irregular inputs lacking the target structure. Never silently alter weights to make them favorable.

Exact public instance names and achievable counts must be resolved in M1. Do not invent archive entries. If fewer eligible cases exist, document this rather than quietly replacing them with favorable cases.

Start with one diagonal layer/block. Use three predeclared generic angles, for example theta in {0.173, 0.619, 1.137} radians, and special angles only as separate diagnostics. Use total block synthesis tolerances {1e-4, 1e-6} initially. These are engineering defaults, not universal FTQC accuracy requirements.

Use a small fixed workspace set, e.g. {0, 8, 32} extra logical qubits, subject to relevance and feasibility. This is an evaluation grid, not the research mechanism. Mark infeasible implementations explicitly. Expand sizes/budgets only after a candidate passes the pilot.

### 4.3 Manifest fields

For every case store source URL, archive/file checksum, dataset path/key, license reference, source revision, graph/Pauli metadata, angle representation, term order, layer boundaries, circuit-generation parameters, selected block, selection rule, and random seeds.

Record whether the input is a complete workload or an extracted block. Do not extrapolate block savings to the whole application without measuring coverage.

## 5. Pipeline and minimal software architecture

Implement a lightweight Python package first. Add optimized kernels only if profiling identifies a bottleneck. Pin dependency versions actually tested. Do not require GPUs, RL training, or a SAT solver for the initial diagnostic pipeline.

    acquisition -> canonical IR -> structure profile -> baseline construction
                -> hypothesis-specific candidates -> equivalence verification
                -> common lowering -> error accounting -> resource scheduling
                -> comparison, ablation, and research decision

Suggested repository layout:

```text
README.md
pyproject.toml
configs/pilot.yaml
data/manifests/
src/collective_phase/
    ir.py
    inputs/
    profiles.py
    baselines/
    candidates/
    lowering/
    verification/
    resources.py
    experiments.py
tests/
results/raw/
reports/
docs/prior-work-matrix.md
docs/decisions.md
docs/progress.md
```

### 5.1 Intermediate representation

Use stable IDs and a declared qubit ordering. Store parity masks as integers or packed bit arrays; phase parameters as symbolic class IDs with precise numeric bindings. Never infer equal angles solely from a loose floating-point tolerance. Preserve coefficients, duplicate terms, constants, global phases, and block boundaries.

Represent reversible computation as a typed DAG with input/output registers, allocation/release events, and cleanup obligations. Represent measurement and correction dependencies explicitly. Every primitive declares its ancilla preconditions and postconditions.

### 5.2 Adapter contracts

Suggested conceptual interfaces, not existing APIs:

```python
load_case(manifest_entry) -> PhaseProgram
profile(program) -> StructuralProfile
compile_method(program, constraints, method_config) -> Candidate | Infeasible
verify(program, candidate) -> VerificationResult
lower(candidate, gate_model, error_budget) -> LoweredCircuit
estimate(lowered, scheduling_model) -> ResourceRecord
```

Each candidate carries method/version, parameters, transformation trace, required resource states, preparation plan, phase convention, and proof obligations. A failed verification prevents performance ranking.

## 6. Baselines to implement

### B0: independent synthesis

Simplify duplicate/same-axis phases exactly where valid. Compute each parity with a CNOT network, apply its phase, and uncompute. Use a verified individual-rotation synthesizer. Special Clifford/T angles should not pass through expensive generic approximation.

### B1: shared parity network plus synthesis

Use an existing compatible network synthesizer or a documented simple parity-sharing method. Preserve the target phase function and include the final linear transformation cleanup. Apply the same rotation synthesizer and precision accounting as other methods.

### B2: ordinary HWP

Implement both full-batch and feasible bounded-workspace batching. For parity predicates, include the cost of making them available to the weight computation. Input parities cannot be replaced by unrelated independent qubits in verification.

Compare a deterministic balanced grouping policy and a modest cost-aware batching policy. If choosing among batch sizes, give both baseline and candidate the same search allowance.

### B3: catalyzed HWP

Reproduce a published construction. Count its catalyst storage, preparation, residual rotation synthesis, arithmetic, and cleanup. Evaluate a full-cost single-use case first; add declared repetition counts such as 10 and 100 to study amortization separately. Different angle values generally need different catalysts. Repeated experimental shots or variational parameter updates do not automatically imply free catalyst reuse.

### B4: compatible joint synthesis

Integrate NCF or another verified implementation only where input semantics, precision, and resource assumptions match. If unavailable, mark it unavailable and narrow conclusions; do not label a home-grown approximation as a reproduction. A pure diagonal block may offer different opportunities from NCF's anticommuting groups.

Before claiming a depth contribution using catalysts, assess the relevance and implementation assumptions of Kim's construction. It need not block an initial noncatalytic pilot, but cannot be ignored in the final novelty comparison.

## 7. Diagnose before designing

For every frozen case compute:

- Number of terms, variables, unique parities, duplicate multiplicities, and exact angle classes.
- Binary rank and dependency structure of parity masks. Rank alone does not imply cheaper integer weight computation.
- Support overlaps and, for graph inputs, degree distribution, connected components, repeated neighborhoods, and candidate dense structures.
- Baseline resource breakdown: parity preparation, weight arithmetic, residual rotations, cleanup, and catalyst preparation.
- Coverage: fraction of original terms and baseline T-cost inside eligible blocks.

Produce reports/diagnosis.md before introducing a complex optimization algorithm. State where the cost actually resides. If residual arithmetic already dominates and the proposed observation does not alter it, say so.

## 8. Candidate mechanisms: examples to test, not mandatory features

Implement at most one mechanism initially, selected using the development cases and literature audit.

### H1: dependence among predicates simplifies integer accumulation

Search small parity sets for cheaper ways to compute the collective phase or the required weight bits. Exact small synthesis may be used as a discovery tool, with a bounded input size and timeout. Record the permitted primitive set and whether any optimality certificate is restricted to it.

Do not stop at a lookup table. Seek a repeated pattern, derive its identity, and specify a detection rule. Compare against optimized HWP with the same resources.

### H2: graph structure replaces edge counting

Diagnostic identities include clique cut count w(n-w) and biclique cut count w_A(b-w_B)+(a-w_A)w_B. They are elementary identities, not novel contributions.

If extending to a decomposition, preserve exact edge multiplicity: a cover is not necessarily a partition. Overlapping groups must not double-count edges. Handle residual edges and signed corrections explicitly. Include multiplication, accumulation, and cleanup costs before declaring savings.

### H3: phase-compatible intermediate reuse

Retain/update an intermediate between compatible groups only when its defining inputs remain unchanged and its cleanup is valid. Compare against an existing retention/recomputation strategy. No reuse across a mixer or noncommuting block without proof.

For every hypothesis write a one-page hypothesis card: observation, nearest prior result, proposed difference, smallest witness, predicted favorable regime, predicted failure regime, and falsification test.

## 9. Correctness and error verification

### 9.1 Exact transformation checks

- For small n (default n <= 10), enumerate all input bitstrings and verify the integer target function and workspace restoration for classical reversible portions.
- For symbolic arbitrary theta, verify exponent equality up to an input-independent constant. Modulo-q equivalence is allowed only under an explicitly restricted angle condition.
- A phase-value comparison does not verify an arbitrary circuit that might mix basis states. Validate the circuit's diagonal/permutation structure or compare its full action on small instances.
- Use independent dense state/unitary checks on very small cases, including coherent superpositions. Include bit-order and sign regression cases.
- For larger constructed transformations, compose proved identities and record transformation certificates. Random testing alone is not a proof.

### 9.2 Measurements and catalysts

For small measurement-assisted gadgets verify branch Kraus operators after corrections or compare channels. Computational-basis truth tables alone can miss lost coherence.

For catalysts verify ideal restoration and absence of unintended entanglement. For approximate catalysts use a compositional error argument; do not assume fresh independent error at every reuse or zero accumulated error without justification. Track resource-state errors separately from gate-approximation errors.

### 9.3 Approximation budget

Initially use an operator-norm budget for deterministic synthesis. A conservative telescoping bound sums local unitary errors. State when equivalence is up to global phase. Do not mix infidelity, operator norm, and diamond distance numerically without a justified conversion.

Allocate one fixed total error budget across each method's actual operations. Equal per-rotation precision is a diagnostic comparison, not necessarily equal total accuracy. If a method has fewer synthesized rotations, record its resulting allocation explicitly. Include catalyst preparation and other approximations in the total bound.

For Hamiltonian simulation, hold the input product formula fixed. Report synthesis error separately from Trotter error. Finite-precision input coefficients and angle rounding must be accounted for or fixed identically.

### 9.4 Meaningful initial tests

Cover zero terms, one term, repeated parity, dependent triple {x,y,x XOR y}, zero/special/generic angles, non-power-of-two batch sizes, insufficient workspace, phase sign, released-ancilla reuse, measurement corrections, and catalysts on entangled inputs. Tests should independently check semantics rather than mirror constructor logic.

## 10. Resource model

Count T and T-dagger equally. Lower Toffoli and other non-Clifford primitives using named verified templates; no universal substitution of every Toffoli with four T gates. Temporary-AND, ordinary unitary Toffoli, and catalytic conversions have different preconditions.

Use separate model profiles where necessary:

- unitary_clifford_t: no mid-circuit measurement; applicable baselines only;
- measurement_assisted_clifford_t: measurements/feedforward allowed with explicit dependencies.

Never compare methods from incompatible profiles in one unlabeled ranking.

T-depth is the T-layer depth of the emitted circuit under a documented scheduler, not a proof of minimum T-depth. Treat Clifford operations as zero T-cost while retaining their causal dependencies. A basic scheduler propagates dependency levels through every operation and increments at T/T-dagger operations. Preserve measurement-to-correction dependencies. Use the same scheduler and postprocessing for all methods.

Report Clifford count and measurement/adaptive-round count as supporting diagnostics; physical runtime is not required.

Peak workspace includes parity scratch, arithmetic scratch, temporary AND registers, catalyst registers, and preparation workspace. Exclude the fixed data register but also report total logical qubits. Release a qubit only when the corresponding cleanup/reset is valid.

For preparation amortization report separately:

    total_T(R) = preparation_T + sum of application_T over R uses
    amortized_T(R) = total_T(R) / R

Do not divide T-depth by R and call it application depth. Report preparation depth, application depth, and the depth of the actual composed schedule. State whether preparation is offline and whether its workspace shares the budget.

Analytical macro estimates are useful for screening. Label them estimated. Final claims require emitted-circuit counts or validated compositional counts with templates and scheduling checks.

## 11. Experimental comparison and ablation

Store one row per case, angle, error budget, workspace budget, method, model profile, and seed. Required fields include:

```text
case_id, source_hash, code_commit, config_hash, method, status,
verification_status, error_metric, error_bound,
T_count, T_depth, peak_workspace, total_qubits,
Clifford_count, measurement_count, adaptive_rounds,
preparation_T, application_T, reuse_count,
compile_seconds, seed, circuit_path, failure_reason
```

Statuses distinguish verified success, infeasible, timeout, verification failure, and unavailable baseline. Never treat missing results as zero cost.

Use paired comparisons on the same cases. Report absolute values, ratios, wins/ties/losses, regressions, coverage, and the best applicable baseline. Do not hide regressions with only an average. Handle zero-denominator ratios explicitly.

Essential ablations:

1. Same primitives, simple grouping versus proposed grouping.
2. Structural transformation disabled.
3. Common postprocessing enabled/disabled for both methods.
4. Catalyst preparation included versus explicitly amortized.
5. Equal total error budgets, with sensitivity to precision.

If stochastic search is introduced, use identical seeds/time allowances and multiple runs. Record actual classical compile time for reproducibility, even though it is not the quantum objective.

Suggested evidence threshold for further investment: a proved mechanism, improvement on more than one independent nontrivial instance, and a resource margin exceeding accounting variation. No arbitrary percentage determines publishability. Prefer a construction with a provable regime of benefit over a small unexplained average gain.

## 12. Milestones and acceptance gates

### M0 — Scope and repository audit

Deliver docs/decisions.md, a dependency plan, and prior-work matrix. Identify reusable code and mismatches. Pin the initial semantic and metric profiles.

Gate: the target, allowed measurements/catalysts, and unsupported claims are explicit.

### M1 — Inputs, IR, and B0

Implement small synthetic cases, public-data loader, frozen manifest, canonical IR, independent synthesis, and core verification.

Gate: at least one real input and all diagnostic semantic tests work. If public access is blocked, complete synthetic infrastructure and report the precise missing resource.

### M2 — Strong HWP baselines and diagnosis

Implement and validate B2 and B3, and a compatible B1. Reproduce small published gadget costs under matching assumptions. Produce baseline resource breakdowns and structural profiles.

Gate: report whether meaningful residual cost and recurring structures exist. Do not start a generic search engine merely because the baselines work.

### M3 — Small witness and hypothesis decision

Select one mechanism. Find a small witness, prove its identity, compile its complete implementation, and test its failure regime. Check direct prior-art overlap again with the precise construction.

Gate: if no verified advantage survives the baseline, record a negative result and stop this mechanism. If a different mechanism is proposed, document the change and evidence first.

### M4 — Minimal detector/rewriter

Implement only the detector and rewrite needed for the witness family. Emit a transformation trace. Evaluate on the frozen pilot plus held-out instances from the same predeclared source categories.

Gate: savings must transfer beyond specially constructed cases; otherwise classify the result as a restricted construction and assess its limited value honestly.

### M5 — Reproducible research package

Produce a final report using the four-question structure, exact commands, locked environment, manifests, raw results, circuit examples, limitations, and nearest-baseline comparisons. Include negative findings and unresolved verification or access issues.

Possible outcomes: continue; narrow to a rigorously characterized family; reframe as tooling; or stop. A negative conclusion is a successful exploration outcome.

## 13. CLI and reproducibility targets

Provide equivalent commands with help text; these names are proposed interfaces to implement:

```bash
python -m collective_phase audit --config configs/pilot.yaml
python -m collective_phase acquire --config configs/pilot.yaml
python -m collective_phase profile --config configs/pilot.yaml
python -m collective_phase run --config configs/pilot.yaml --methods independent,shared_parity,hwp,catalyzed_hwp
python -m collective_phase verify --results results/raw
python -m collective_phase report --results results/raw
```

Add a tiny smoke configuration that runs without large downloads. Cache expensive synthesis by angle, tolerance, gate model, and synthesizer version. Checkpoints must survive interruption. Never silently replace a timeout with a different precision. Keep source data immutable and generated circuits/results separate.

For each milestone update docs/progress.md with completed work, evidence, unresolved risks, exact reproduction commands, and next bounded action. Keep setup failures distinct from negative scientific results.

## 14. Required final artifacts from local Codex

- Working prototype and installation/reproduction instructions.
- Frozen benchmark manifest with source identities and checksums.
- Prior-work matrix and hypothesis cards.
- Verified small circuit witness, or documented unsuccessful search.
- Baseline and candidate circuits plus transformation traces.
- Machine-readable raw results and a concise comparison report.
- Resource-accounting and approximation-model documentation.
- Final four-part research assessment: observation, gap, verification, and potential.

## 15. Potential extensions, conditional on evidence

If the initial mechanism works, investigate related angle classes, general commuting Pauli blocks, broader phase predicates, or compatible inter-block reuse. Each extension needs new semantic and baseline checks.

Do not promise applicability to all QAOA, all Hamiltonian simulation, integer factoring, or arbitrary Clifford+T optimization from a result on one diagonal block family.

The immediate goal is one defensible observation with a verified construction and public-benchmark evidence. The compiler should grow only as that evidence requires.

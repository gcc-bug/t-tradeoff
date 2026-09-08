# Prior Work Matrix

Checked against current arXiv metadata and linked repositories on 2026-09-07.
An unsuccessful code search is recorded as unverified availability, not as
evidence that no implementation exists.

| Source and checked version | Exact location used | Gate/metric model and applicable input | Implementation status | Overlap with this prototype |
| --- | --- | --- | --- | --- |
| Ross-Selinger, *Optimal ancilla-free Clifford+T approximation of z-rotations*, arXiv:1403.2975v3 (2016) | synthesis algorithm and typical T-count discussion | ancilla-free Clifford+T approximation of one `Rz` | `pygridsynth==2.0.0` verified on PyPI/GitHub as an implementation based on gridsynth | supplies B0/B1/candidate rotation synthesis; no collective predicate optimization |
| Gidney, *Halving the cost of quantum addition*, arXiv:1709.06648v3 (2018) | temporary logical-AND construction and measurement uncompute | 4-T AND compute, zero-T measurement cleanup | paper circuit; no external package required for macro count | underlies measurement-assisted arithmetic assumptions; cleanup channel still needs emitted validation here |
| Kivlichan et al., *Improved Fault-Tolerant Quantum Simulation...*, arXiv:1902.10673v4 (2020) | Sec. 2.1 and Appendix A.1-A.2 | HWP, bounded workspace, T/Toffoli counts | paper formulas implemented as B2 semantic/resource macros | nearest ordinary HWP baseline; assumes input rotation qubits are available, so this prototype separately charges parity materialization |
| Campbell, *Early fault-tolerant simulations of the Hubbard model*, arXiv:2012.09238v4 (2024 update) | Appendix E and corrected gate-count discussion | explicit Hubbard/Trotter non-Clifford accounting | paper formulas reviewed; reproduction not yet added | guards against omitting arithmetic and cleanup in simulation claims |
| Kan-Symons, *Resource-optimized fault-tolerant simulation...*, arXiv:2411.02160v2 (2025) | “Space-time trade-off in HWP” and Supplementary Note 3 | baseline/catalyzed HWP, Toffoli and logical-qubit counts | B3 ideal macro and formulas implemented; internal circuit emission pending | essential catalytic baseline; catalyst preparation, distinct angles, storage, and reuse are explicit |
| Gidney-Fowler, *Efficient magic state factories with a catalyzed CCZ to 2T transformation*, arXiv:1812.01238v3 (2019) | generalized phase-catalysis discussion and circuits | catalyst resource-state semantics and factory cost | paper only in this prototype | motivates catalyst restoration/error obligations; not a clean-ancilla substitution |
| Kim, constant-T-depth catalytic rotations, arXiv:2506.15147 | current arXiv version and depth construction location still pending full audit | catalytic T-depth | not integrated | must be resolved before any catalytic depth claim; none is made here |
| Li et al., *Non-Clifford Fusion: T-Gate Optimization for Quantum Simulation*, arXiv:2510.13573v1 (2025) | grouping/synthesis method and reported benchmark precision settings | joint synthesis of small transformed Pauli groups; T-count/depth | exact public artifact not confirmed; B4 reports `unavailable` | potential joint-synthesis competitor; published loose two-qubit tolerances are not transferred |
| Meuli et al., *Reversible Pebbling Game for Quantum Memory Management*, arXiv:1904.02121v1 (2019) | cleanup scheduling/SAT formulation | reversible recomputation/workspace tradeoff | not integrated | nearest general retention/recomputation framework; H1 currently performs only local cleanup |
| Gidney, “Computed phasing” (Algassert, web article) | compute-function/apply-phase/uncompute pattern | conceptual reversible phasing | public explanation, no pinned software artifact | directly overlaps the general mechanism; H1's only distinction is its detected Boolean identity |
| Rajakumar et al., *Generating Target Graph Couplings for QAOA...*, arXiv:2011.08165v2 (2022) | graph-coupling constructions and MIP | global Ising controls, operation count | no compatible Clifford+T baseline integrated | related graph structure under different native primitives, not interchangeable with parity-phase synthesis |
| Dinpazhouh-Hicks, *Optimizing Cost Hamiltonian Compilation for Max-Cut QAOA...*, arXiv:2509.00170v1 (2025) | structural bounds and graph-family results | global controls and bit flips | no compatible Clifford+T baseline integrated | graph-structural comparison under a different hardware objective |
| Graph sparsification/decomposition for QAOA, arXiv:2406.14330 | current version requires deeper claim-by-claim audit | changed/decomposed graph objectives and hardware considerations | not integrated | cannot serve as an exact target-preserving Clifford+T baseline without an adapter proof |

## Data and compiler components

| Source | Checked revision/status | Use |
| --- | --- | --- |
| QED-C application benchmarks | Git revision `feb22a900d9d94d40e81bc1d25e149bd8f3cbc18`; Apache-2.0 | three checksum-pinned MaxCut pilot files |
| HamLib | public NERSC portal reachable; archive subset/license audit incomplete | spin-model pilot remains pending |
| simcount | Git HEAD reachable at `1e40e551965cf6009c87016219621fd9bf18f6fc`; compatibility not audited | unavailable baseline/sample source |
| Rustiq | Git HEAD reachable at `425000222e21a7a28d70a08c75be968f16fd6903`; compatibility not audited | possible future parity-network component, not a T synthesizer |


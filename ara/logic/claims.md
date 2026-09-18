# Claims

These claims summarize stored development evidence; no experiments were rerun during ARA initialization.

## C01: Preference recomputation has no demonstrated endpoint advantage
- **Statement**: Updating preference vectors has not demonstrated an endpoint advantage over retaining initial priorities in the recorded matched studies.
- **Conditions**: The bounded action library, shared seeds, configured budgets, and recorded development workloads; this does not generalize to other search spaces or held-out workloads.
- **Sources**: []
- **Status**: supported
- **Falsification criteria**: A matched study in this regime finds a verified endpoint improvement attributable to recomputation, with action availability and compilation budgets controlled.
- **Proof**: [E01, E02, E03]
- **Evidence basis**: Frozen-priority comparisons in the archived balanced, depth, and count reports.
- **Tags**: policy-ablation, development-only

## C02: Fixed pass composition can reproduce the discovered tradeoff
- **Statement**: A fixed count-then-depth composition reproduces the discovered constrained optimum among the explored candidates, so adaptive ordering and scratch reuse are not necessary for that observed endpoint.
- **Conditions**: The recorded single-demonstration development instance and tested seed/action catalog only; optimum means best explored candidate, not a global optimum. The optional Feynman executable was unavailable in this run.
- **Sources**: []
- **Status**: supported
- **Falsification criteria**: Replaying the fixed composition under the same constraints fails to recover the endpoint, or a matched expanded evaluation establishes an improvement that depends on adaptive ordering or reuse.
- **Proof**: [E04]
- **Evidence basis**: Reference outcomes, winner chain, counterfactuals, and conclusion in the archived single-demonstration report; raw result and circuit pointers in the evidence log index.
- **Tags**: fixed-sequence, counterfactual

## C03: Clean workspace can reduce phase depth without reducing T-count
- **Statement**: Parallelizing supported phase regions with clean workspace can lower scheduled T-depth while leaving T-count unchanged.
- **Conditions**: Exact phase diagnostic and the limited clean-scratch CNOT/diagonal action; all added wires must be restored. This is a reproduction of a known tradeoff, not a novelty claim.
- **Sources**: []
- **Status**: supported
- **Falsification criteria**: Independent scheduling or clean-isometry verification removes the reported depth benefit or finds unreturned workspace under the declared gate model.
- **Proof**: [E02, E03, E04]
- **Evidence basis**: Pareto points in the depth/count diagnostics and direct-workspace counterfactual in the single demonstration.
- **Tags**: ancillas, scheduling, exact-rewrite

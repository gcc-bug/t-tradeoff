# Concepts

## Affine parity phase
- **Definition**: A predicate is parity(mask & x) XOR offset; its weighted angle contributes to an integer sum in the target complex phase, not an XOR sum.

## Hamming-weight phasing (HWP)
- **Definition**: Compute the binary weight of equal-angle predicates, phase the weight bits, and clean up the arithmetic. The active implementation uses staged compressors with unitary reversal.

## Resource tuple
- **Definition**: (T-count, scheduled T-depth, allocated additional logical clean qubits), measured from emitted circuits under the declared gate model.

## Exact post-synthesis rewrite
- **Definition**: An equivalence-checked transformation of the already lowered Clifford+T circuit; it consumes no additional approximation-error allocation.

## Frozen versus adaptive preferences
- **Definition**: Frozen priorities retain their initial resource preferences, while adaptive priorities recompute them during bounded exploration; both use the same immutable final objective.

## Clean scratch certificate
- **Definition**: Explicit evidence that scratch wires are returned clean by a local phase action, permitting certified reuse by a later compatible local action. Idle wires are not assumed clean.

Sources: repository semantic/resource contracts, review guide, and backend applicability documentation.

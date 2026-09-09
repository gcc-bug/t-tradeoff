# HWP Implementation Audit

Audit date: 2026-09-09.

## Sources

The primary source is Kivlichan et al., *Improved Fault-Tolerant Quantum
Simulation of Condensed-Phase Correlated Electrons via Trotterization*,
arXiv:1902.10673v4 (the CC BY 4.0 revision), Appendix A.1, "Combining
arbitrary parallelizable rotations by Hamming weight phasing." The relevant
passages define weight-bit phasing, the staged three-input and two-input
adders, the `n - 1` worst-case bound, and measurement-assisted uncomputation.

The primitive cleanup assumptions were cross-checked against Gidney, *Halving
the cost of quantum addition*, arXiv:1709.06648v3, Figures 2 and 3 and the
Hamming-weight example: a temporary logical AND costs four T gates to compute
and zero T gates plus measurement/feedforward to erase.

The maintained implementation consulted was Qualtran
`qualtran.bloqs.arithmetic.hamming_weight.HammingWeightCompute` at Git revision
`d5faa99db850001d440d0cc4e05b7b20b249a652` (2026-09-04), Apache-2.0. It uses
the same staged 3-to-2 compressor and reports `n - popcount(n)` ANDs. No
Qualtran code is vendored or imported; its implementation was used to audit
the local gate ordering and exact count.

## Local Mapping

| Source primitive | Local implementation | Emitted action |
| --- | --- | --- |
| Three equal-weight inputs plus clean carry | `append_three_to_two_compressor` | five CNOTs and one Toffoli; two inputs retained as garbage, third becomes sum, carry becomes next weight |
| Even final pair plus clean carry | `append_two_to_two_adder` | one Toffoli and one CNOT; second input becomes sum |
| Repeated weight stages | `hamming_weight_compute` | triples are reduced at each weight, an odd survivor becomes the output bit, and carries feed the next stage |
| Weight-bit rotations | `_emit_adder_batch` | `P(2^j theta)` on each surviving weight-`2^j` bit |
| Cleanup | `_emit_adder_batch` | reverse every arithmetic operation, then reverse parity preparation |

The local construction materializes every parity predicate first because this
repository starts from parity functions, while the paper starts from qubits on
which equal rotations are already available. For a batch of size `n > 1`, the
local peak workspace is therefore

```text
n parity qubits + (n - popcount(n)) clean carry qubits.
```

The forward arithmetic contains exactly `n - popcount(n)` Toffolis. The
unitary cleanup contains the same number, so the actual emitted candidate has
`2 * (n - popcount(n))` logical Toffolis before the shared exact 7-T lowering.
This is not the measured construction's T count. The paper and Qualtran can
use temporary-AND measurement cleanup; the default unitary profile cannot.

Every batch trace records parity wires, surviving output-weight wires, retained
garbage, carry wires, stage widths, forward and cleanup Toffolis, rotations,
and the source. Tests exhaust primitive truth tables and full population-count
computation/inversion for sizes 1-8, including non-powers of two.

## ANF Reference

`population_count_compute` is now explicitly a small correctness reference,
capped at eight inputs. It enumerates elementary-symmetric monomials and is not
ordinary HWP arithmetic. Its observed forward Toffoli counts of 3 at size 3
and 391 at size 8 remain code observations, not bounds. It is excluded from the
default configuration and evidence ranking.

## Scope Limits

This audit establishes a credible unitary adaptation of ordinary staged-adder
HWP and derives resources from its emitted circuit. It does not reproduce the
measurement-assisted cleanup cost, prove minimum depth or workspace, or cover
the square-root-workspace scheme in Appendix A.2. Parity CNOT optimization is
also independent of the HWP arithmetic and remains represented only by the
basic shared-parity reference.

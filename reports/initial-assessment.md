# Initial Research Assessment

Date: 2026-09-07

Configuration: `configs/pilot-initial.yaml`.  This bounded decision run uses all
13 frozen manifest cases, one generic angle (`0.173`), total operator-norm
synthesis budget `1e-4`, eight extra logical qubits, and the unitary profile.
All 50 successful rows pass exhaustive phase/workspace checks and stored
artifact validation.  Macro rows verify ideal semantics rather than an emitted
implementation.  Two weighted controls correctly reject equal-angle HWP.

## Observation

The exact identity `a + b + (a XOR b) = 2(a OR b)` removes two generic rotations
per selected dependent triple at the cost of two emitted unitary Toffolis.  The
detector selected triples in each of the three checksum-pinned public QED-C
graphs.

| Public case | B0/B1 T | H1 T | H1/B0 | B2 T | H1 workspace | H1 T-depth | B0 T-depth |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `qedc_mc_004_003_000` | 312 | 214 | 0.686 | 228 | 3 | 208 | 260 |
| `qedc_mc_006_003_000` | 468 | 282 | 0.603 | 354 | 3 | 170 | 260 |
| `qedc_mc_008_003_000` | 624 | 444 | 0.712 | 600 | 3 | 276 | 260 |

B0, B1, and H1 are emitted counts.  B2 is a published compositional macro
estimate and has unknown Clifford count; it is shown only as a diagnostic, not
as an equally validated ranking.  H1's T-depth regression on the 8-vertex case
shows that the current construction is not a depth improvement.

Across all 13 cases H1 records 6 wins, 7 ties, and 0 T-count losses against the
best emitted B0/B1 result.  Ties are the expected failure regime where no
eligible disjoint triple is selected.  The special-angle smoke suite yields no
wins and includes regressions, also as predicted.

## Gap

The result does not establish that a production HWP compiler, Boolean phase
optimizer, phase-polynomial optimizer, or NCF implementation misses the same
identity.  B2 arithmetic is not emitted, B3 is macro-accounted, and B4 is
unavailable under matching precision semantics.  The public inputs are three
sizes from one QED-C generator family; the HamLib spin subset is still absent.

## Verification

- Input files match manifest SHA-256 digests at a fixed public revision.
- Every small candidate is checked on all basis states for phase, unchanged
  data, and zero returned workspace.
- Independent coherent-state propagation is used where total state size is
  feasible; other cases rely on the proved basis-preserving operation set.
- Generic rotations come from `pygridsynth==2.0.0`, and each synthesized matrix
  is checked directly against `Rz(theta)` in operator norm.
- All methods receive one total error budget over their actual synthesized
  rotations.  Stored public-row bounds are below `1e-4`.
- The reported scheduler preserves all gate dependencies but makes no minimum
  T-depth claim.

## Potential

Continue H1 narrowly.  The next gate is an emitted, channel-checked ordinary
HWP implementation under the same workspace and synthesis budget, followed by
a targeted prior-art audit for this precise dependent-triple rewrite.  Only
then should the full three-angle/two-tolerance grid or additional source
families run.  If the advantage disappears, record the identity as a restricted
negative result and stop expanding this mechanism.

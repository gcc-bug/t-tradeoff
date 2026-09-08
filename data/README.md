# Data

`manifests/` is tracked and freezes source identity, selection rules, checksums,
and generator parameters.  `raw/` is immutable, ignored, and populated only by
`python -m collective_phase acquire`.  A pre-existing file is never overwritten:
it must match the declared SHA-256 digest or acquisition fails.

The current public pilot uses QED-C MaxCut edge lists at revision
`feb22a900d9d94d40e81bc1d25e149bd8f3cbc18` under Apache-2.0.  HamLib spin
blocks remain an M1 acquisition gap; no substitute is labeled as public data.


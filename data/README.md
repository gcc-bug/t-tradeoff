# Data

`manifests/` is tracked and freezes source identity, selection rules, checksums,
and generator parameters.  `raw/` is immutable, ignored, and populated only by
`python -m collective_phase acquire`.  A pre-existing file is never overwritten:
it must match the declared SHA-256 digest or acquisition fails.

`refocus-study.yaml` contains three QED-C MaxCut edge lists at revision
`feb22a900d9d94d40e81bc1d25e149bd8f3cbc18` under Apache-2.0, plus synthetic
development controls. `adaptive-development.yaml` contains one synthetic
mechanism witness and one weighted negative control. All influenced development
and are not held-out evidence. No substitute is labeled as public data.

# HWP Pareto validation record

Validation for the source fingerprint
`c3c3b0d482b0bb474fac66c692028e106f22e755f75049c4d6a7b3c16bcec71b`
and config checksum recorded in [the study](hwp-pareto-study.md).
Commands ran in the isolated worktree using the existing project Python environment.

```text
PYTHONPATH=src python -m pytest -q
129 passed in 11.67s

PYTHONPATH=src python scripts/run_hwp_pareto.py --plot
All nine searches: OPTIMAL; all nine baseline enumerations complete.

PYTHONPATH=src python scripts/run_hwp_pareto.py --verify
Verified 158 templates, 52 complete parents, 52 optimized children and the tracked witness.
```

Tests compare the model with independent tiny partition/wave enumeration and
check composition, precision allocation, scratch reuse, serialization replay,
mutation rejection, and timeout/infeasibility behavior. Saved-evidence replay
checks source/config/artifact checksums, circuit semantics and resources; it
does not establish optimality beyond the declared library and wave model.

The initial baseline diagnostic is superseded. Its seven removed apparent
gains are documented in the study rather than counted as improvements.

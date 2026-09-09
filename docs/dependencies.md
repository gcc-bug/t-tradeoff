# Dependency Plan

The active experiment is CPU-only and has no solver, GPU, or training
dependency. PyZX supplies exact whole-circuit optimization and equivalence
checking after approximate rotation synthesis.

| Dependency | Pin | Purpose | Reproducibility note |
| --- | --- | --- | --- |
| Python | `>=3.10` | package and CLI | tested version is recorded by the environment |
| PyYAML | `6.0.2` | structured configs and manifests | exact direct pin |
| NumPy | `>=1.24,<3` | dense verification and operator norms | bounded compatibility range |
| pygridsynth | `2.0.0` | generic ancilla-free `Rz` synthesis | exact direct pin; synthesis result stores backend version and measured error |
| PyZX | `0.9.0` | exact Clifford+T optimization and equivalence | exact direct pin; output is independently reduced against its input and global phase is corrected explicitly |
| pytest | `>=8,<9` | tests | optional `test` extra |

`pygridsynth` has transitive scientific-Python dependencies.  The lock is not
yet fully transitive; M5 requires generating and testing a platform-appropriate
lock file.  Rotation cache keys contain the exact angle representation,
tolerance, backend version, and random seed.  Cached entries retain the
measured operator-norm error.

Feynman is an optional external executable rather than a Python dependency.
The tested depth adapter uses the BSD-2-Clause `v0.1.0` Linux release at commit
`2b52a0a78c10999cfc4c1d9c76c994c471cf2350`. Its `.qc` interface declares all
data and workspace wires as primary inputs and outputs; the adapter requests
Feynman's own verification and then independently checks the result with PyZX.
The current source revision `d2c382a2ab43a40a87f12f4255645bbb55f704f8`
advertises the POPL 2025 relational passes, but was not built in this
environment because Cabal and GHC are unavailable.

Public input acquisition uses only Python's standard library.  Downloads are
accepted only when their SHA-256 digest matches the frozen manifest, and an
existing mismatched file is never overwritten.

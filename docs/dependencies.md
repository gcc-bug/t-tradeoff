# Dependency Plan

The initial prototype is deliberately CPU-only and has no solver, GPU, quantum
SDK, or training dependency.

| Dependency | Pin | Purpose | Reproducibility note |
| --- | --- | --- | --- |
| Python | `>=3.10` | package and CLI | tested version is recorded by the environment |
| PyYAML | `6.0.2` | structured configs and manifests | exact direct pin |
| NumPy | `>=1.24,<3` | dense verification and operator norms | bounded compatibility range |
| pygridsynth | `2.0.0` | generic ancilla-free `Rz` synthesis | exact direct pin; synthesis result stores backend version and measured error |
| pytest | `>=8,<9` | tests | optional `test` extra |

`pygridsynth` has transitive scientific-Python dependencies.  The lock is not
yet fully transitive; M5 requires generating and testing a platform-appropriate
lock file.  Rotation cache keys contain the exact angle representation,
tolerance, backend version, and random seed.  Cached entries retain the
measured operator-norm error.

Public input acquisition uses only Python's standard library.  Downloads are
accepted only when their SHA-256 digest matches the frozen manifest, and an
existing mismatched file is never overwritten.


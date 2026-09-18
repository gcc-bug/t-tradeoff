# Environment

- **Language/runtime**: Project requires Python >=3.10; exact installed versions and stored run environment are recorded in `evidence/environment.json`.
- **Key dependencies**: `pygridsynth==2.0.0`, `pyzx==0.9.0`, `PyYAML==6.0.2`, `numpy>=1.24,<3`; test extra `pytest>=8,<9`. Source: `pyproject.toml`.
- **Hardware**: Not remeasured during artifact initialization; consult stored run metadata where present. Do not infer comparable wall time across machines.
- **Data sources**: Checksum-pinned QED-C development graphs and synthetic diagnostics; see `data/manifests/` through the code/config index.
- **Protocols**: Fixed error/resource contracts, verified parent chains, common seeds, recorded failures and compilation budgets.
- **Random seeds**: Declared per configuration; the single-demonstration configuration uses seed 0.
- **Code location**: Canonical source stays in the repository; `src/artifacts.md` links every tracked source/config/test/script file. No code is duplicated into ARA.
- **Reproduce**: From the repository root, run `.venv/bin/python scripts/inspect_tradeoff_sequences.py --config configs/single-demonstration.yaml`. This was not run during ARA installation.
- **ARA installer**: `@ara-commons/ara-skills@0.9.0`, validated using Node.js 22.14.0 and npm 8.5.1 with TLS verification enabled; package integrity is in `.research-repo.yml` and `scripts/setup-ara.sh`.

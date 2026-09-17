# Private research artifact

ARA is installed project-locally from `@ara-commons/ara-skills@0.9.0`.
The publication profile is `undecided`, which applies double-blind safeguards.
The working `ara/` and `.codex/skills/` directories are ignored by Git.

The installed inventory is `research-manager`, `compiler`, `rigor-reviewer`,
`research-visualizer`, `research-foresight`, and `context-drop`. Publishing is
disabled and `submit-ara` is absent. Do not use upstream `update` or `--all`:
they also install publishing capabilities.

Reinstall from the repository root with Node.js >=18 and npm on `PATH`:

```bash
bash scripts/setup-ara.sh
```

The script refuses `NODE_TLS_REJECT_UNAUTHORIZED=0`, forces npm certificate
verification, checks the registry integrity against the recorded pin, and
installs only the private inventory. Initialization was validated with
Node.js 22.14.0 and npm 8.5.1. Use your normal trusted certificate configuration
when working behind a proxy; never disable verification.

Start with `ara/PAPER.md` (an artifact manifest, not a manuscript).
The initial compilation covers the single demonstration, balanced policy
comparison, depth/count diagnostics, implementation contracts, and prior-work
matrix. Older result files remain individually indexed without promoting them
to current evidence. Research experiments were not rerun during installation.

Routing in `AGENTS.md` captures research milestones at task completion.
Read-only reviews do not trigger writes. Ask to compile new evidence, inspect
the local process map, or query the artifact as needed. Recommendations remain
proposals until adopted; installation does not authorize a research pivot.

With the organizer skill installed, validate the lifecycle using its
`scripts/check_research_lifecycle.py` against this repository. That checks
wiring and basic structure, not independent rigor or anonymity. A future
release needs a separate sanitized snapshot and explicit sharing approval.

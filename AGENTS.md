# Project instructions

## ARA: agent-native research artifacts

This project maintains a private research artifact in `ara/`. Read
`.research-repo.yml` for publication and lifecycle policy. Discover installed
skills through `.codex/skills/.ara-skills.json` and read the corresponding
`.codex/skills/<name>/SKILL.md` before use. Reinstall with
`bash scripts/setup-ara.sh` using Node.js >=18 and normal TLS verification.

- `/research-manager` — automatically capture research milestones once at the end of the task into private `ara/`; skip greetings, formatting-only work, read-only reviews/audits/status requests, and any turn where writes are prohibited. Distinguish proposed directions from decisions actually adopted by the user.
- `/compiler` — on demand, compile existing code, documentation, and results into private `ara/`; use anonymous metadata and never invent results or a manuscript.
- `/rigor-reviewer` — verify evidence and claims before trusting or sharing; this writes a report and requires a separate anonymity audit before sharing.
- `/research-visualizer` — inspect or export the trajectory locally; serve on loopback only and never publish a working-artifact visualization in blind mode.
- `/research-foresight` — answer research questions read-only against private `ara/` with source citations and explicit uncertainty.
- `/context-drop` — require explicit approval and a separately sanitized snapshot; never send the canonical repository or working `ara/`.
- `/submit-ara` — disabled and uninstalled in `undecided` or `double-blind` mode; never invoke it until the user explicitly changes the publication profile and authorizes publication.

These blind-mode restrictions override upstream sharing, publishing, and paper
badge defaults. Keep the manuscript separate, omit public project/paper links
and badges, and exclude working ARA, local skills, and canonical Git history
from anonymous exports. Do not run upstream `update` or install `--all`, which
would add publishing skills. Keep `ara/` and `.codex/skills/` ignored and untracked.

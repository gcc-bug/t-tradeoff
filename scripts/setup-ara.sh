#!/usr/bin/env bash
# Install the reviewed private bundle. Do not use upstream `update` or `--all`:
# those also install the publishing capability.
set -euo pipefail
ara_package='@ara-commons/ara-skills@0.9.0'
ara_integrity='sha512-sgFepbf8Xfz1hMqAqEMPgqYnJxj973HrPuvgoF16nwZqTffSwVdguT/5yGoN1gTSlB+r7nEeoTOP/qMHZAEqxQ=='
if [[ ${NODE_TLS_REJECT_UNAUTHORIZED:-} == 0 ]]; then
  echo 'Refusing disabled TLS verification. Run with NODE_TLS_REJECT_UNAUTHORIZED unset.' >&2
  exit 1
fi
node -e 'if (Number(process.versions.node.split(".")[0]) < 18) { console.error("ARA requires Node.js >=18 on PATH"); process.exit(1); }'
export npm_config_strict_ssl=true
export npm_config_registry=https://registry.npmjs.org
export npm_config_ignore_scripts=true
ara_actual_integrity=$(npm view "$ara_package" dist.integrity)
if [[ "$ara_actual_integrity" != "$ara_integrity" ]]; then
  echo 'ARA registry integrity differs from the reviewed pin.' >&2
  exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
npx --yes "$ara_package" install \
  --skill research-manager --skill compiler --skill rigor-reviewer \
  --skill research-visualizer --skill research-foresight --skill context-drop \
  --agent codex --local
npx --yes "$ara_package" list

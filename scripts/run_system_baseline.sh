#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf 'Running Day 1 environment collection...
'
bash "${ROOT_DIR}/scripts/collect_env.sh"

printf '
Next: fill docs/environment/jetson_system_snapshot.md and docs/reports/day1_environment_check.md from artifacts/system/jetson_env_raw.log
'

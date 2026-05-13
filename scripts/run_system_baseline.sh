#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_FILE="${ROOT_DIR}/results/system/system_baseline_${STAMP}.json"
TEGRSTATS_LOG="${ROOT_DIR}/artifacts/system/tegrastats_system_baseline_${STAMP}.log"
PID=""

mkdir -p "${ROOT_DIR}/results/system" "${ROOT_DIR}/artifacts/system"

cleanup() {
  if [ -n "${PID}" ] && kill -0 "${PID}" >/dev/null 2>&1; then
    kill "${PID}" >/dev/null 2>&1 || true
    wait "${PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "${TEGRSTATS_LOG}" 2>&1 &
  PID="$!"
else
  printf 'tegrastats unavailable; benchmark will run without thermal/power side log\n' >&2
  TEGRSTATS_LOG=""
fi

python3 "${ROOT_DIR}/benchmarks/system/system_smoke_bench.py" \
  --output "${RESULT_FILE}" \
  --tegrastats-log "${TEGRSTATS_LOG}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

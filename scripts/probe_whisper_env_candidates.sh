#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_REL="results/inference/whisper_env_candidates_${STAMP}.json"
REPORT_REL="docs/reports/whisper_env_candidate_probe.md"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"
TARGET_ENV="${WHISPER_CONDA_ENV_NAME:-whisper_env}"

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports"

python3 "${ROOT_DIR}/benchmarks/inference/whisper_env_candidate_probe.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --target-env "${TARGET_ENV}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"

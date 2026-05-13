#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_REL="results/inference/ort_cuda_wheel_candidates_${STAMP}.json"
REPORT_REL="docs/reports/onnxruntime_cuda_env_candidate_probe.md"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports"

python3 "${ROOT_DIR}/benchmarks/inference/ort_cuda_wheel_candidate_probe.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"

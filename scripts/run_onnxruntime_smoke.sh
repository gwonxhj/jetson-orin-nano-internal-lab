#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_REL="results/inference/onnxruntime_resnet18_cpu_${STAMP}.json"
REPORT_REL="docs/reports/onnxruntime_inference_smoke.md"
TEGRSTATS_REL="artifacts/system/tegrastats_onnxruntime_resnet18_${STAMP}.log"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
PID=""

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/artifacts/system" "${ROOT_DIR}/docs/reports"

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
  printf 'tegrastats unavailable; ONNX Runtime smoke will run without thermal/power side log\n' >&2
  TEGRSTATS_REL=""
  TEGRSTATS_LOG=""
fi

python3 "${ROOT_DIR}/benchmarks/inference/onnxruntime_image_smoke.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --onnx "models/resnet18_random_seed42_opset17.onnx" \
  --tensorrt-json "results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json" \
  --provider "CPUExecutionProvider" \
  --tegrastats-log "${TEGRSTATS_REL}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

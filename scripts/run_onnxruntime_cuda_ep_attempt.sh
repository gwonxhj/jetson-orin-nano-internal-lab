#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_REL="results/inference/onnxruntime_cuda_ep_attempt_${STAMP}.json"
REPORT_REL="docs/reports/onnxruntime_cuda_ep_activation_attempt.md"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports"

python3 "${ROOT_DIR}/benchmarks/inference/onnxruntime_cuda_ep_attempt.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --onnx "models/resnet18_random_seed42_opset17.onnx" \
  --provider "CUDAExecutionProvider"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"

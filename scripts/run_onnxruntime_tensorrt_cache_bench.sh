#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
RESULT_REL="results/inference/onnxruntime_tensorrt_cache_bench_${STAMP}.json"
REPORT_REL="docs/reports/onnxruntime_tensorrt_cache_bench.md"
CACHE_REL="artifacts/tensorrt/ort_trt_engine_cache/resnet18_fp32"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"
CACHE_DIR="${ROOT_DIR}/${CACHE_REL}"

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports" "${CACHE_DIR}"

if ! command -v conda >/dev/null 2>&1; then
  if [ -f "${HOME}/miniconda3/etc/profile.d/conda.sh" ]; then
    # shellcheck source=/dev/null
    source "${HOME}/miniconda3/etc/profile.d/conda.sh"
  fi
fi

conda run -n ort_cuda_env python "${ROOT_DIR}/benchmarks/inference/onnxruntime_tensorrt_cache_bench.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --onnx "models/resnet18_random_seed42_opset17.onnx" \
  --tensorrt-json "results/tensorrt/resnet18_fp16_trtexec_20260513_125323.json" \
  --cache-dir "${CACHE_DIR}" \
  --cache-prefix "resnet18_fp32" \
  --warmup 10 \
  --repeat 50 \
  --clear-cache

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
printf 'Wrote/updated cache: %s\n' "${CACHE_DIR}"

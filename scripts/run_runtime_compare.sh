#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT="${ROOT_DIR}/results/runtime_compare/resnet18_pytorch_cuda_fp32_vs_onnxruntime_cpu_fp32_vs_tensorrt_fp16_${STAMP}.json"
REPORT="${ROOT_DIR}/docs/reports/runtime_comparison.md"

python3 "${ROOT_DIR}/benchmarks/runtime_compare/build_runtime_comparison.py" \
  --output "${OUTPUT}" \
  --markdown "${REPORT}"

printf 'Wrote runtime comparison: %s\n' "${OUTPUT}"
printf 'Wrote report: %s\n' "${REPORT}"

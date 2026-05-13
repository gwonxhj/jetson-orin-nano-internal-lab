#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL="${1:-resnet18}"
RESULT_FILE="${ROOT_DIR}/results/tensorrt/${MODEL}_fp16_trtexec_${STAMP}.json"
ONNX_FILE="${ROOT_DIR}/models/${MODEL}_random_seed42_opset17.onnx"
ENGINE_FILE="${ROOT_DIR}/artifacts/engines/${MODEL}_fp16_${STAMP}.engine"
BUILD_LOG="${ROOT_DIR}/artifacts/tensorrt/${MODEL}_fp16_build_${STAMP}.log"
RUN_LOG="${ROOT_DIR}/artifacts/tensorrt/${MODEL}_fp16_run_${STAMP}.log"
TEGRSTATS_LOG="${ROOT_DIR}/artifacts/system/tegrastats_tensorrt_${MODEL}_${STAMP}.log"
PID=""

mkdir -p "${ROOT_DIR}/models" "${ROOT_DIR}/results/tensorrt" "${ROOT_DIR}/artifacts/engines" "${ROOT_DIR}/artifacts/tensorrt" "${ROOT_DIR}/artifacts/system"

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
  printf 'tegrastats unavailable; TensorRT smoke will run without thermal/power side log\n' >&2
  TEGRSTATS_LOG=""
fi

python3 "${ROOT_DIR}/benchmarks/tensorrt/resnet18_trtexec_smoke.py" \
  --output "${RESULT_FILE}" \
  --onnx "${ONNX_FILE}" \
  --engine "${ENGINE_FILE}" \
  --build-log "${BUILD_LOG}" \
  --run-log "${RUN_LOG}" \
  --tegrastats-log "${TEGRSTATS_LOG}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote ONNX: %s\n' "${ONNX_FILE}"
printf 'Wrote engine: %s\n' "${ENGINE_FILE}"
printf 'Wrote build log: %s\n' "${BUILD_LOG}"
printf 'Wrote run log: %s\n' "${RUN_LOG}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL="${1:-resnet18}"
DEVICE="${2:-auto}"
RESULT_FILE="${ROOT_DIR}/results/inference/pytorch_${MODEL}_${STAMP}.json"
TEGRSTATS_LOG="${ROOT_DIR}/artifacts/system/tegrastats_inference_${MODEL}_${STAMP}.log"
PID=""

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/artifacts/system"

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
  printf 'tegrastats unavailable; inference smoke will run without thermal/power side log\n' >&2
  TEGRSTATS_LOG=""
fi

python3 "${ROOT_DIR}/benchmarks/inference/pytorch_image_smoke.py" \
  --output "${RESULT_FILE}" \
  --model "${MODEL}" \
  --device "${DEVICE}" \
  --tegrastats-log "${TEGRSTATS_LOG}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

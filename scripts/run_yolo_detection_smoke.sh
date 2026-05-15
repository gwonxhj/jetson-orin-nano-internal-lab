#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL="${1:-yolov8n.pt}"
DEVICE="${2:-auto}"
RESULT_FILE="${ROOT_DIR}/results/inference/yolo_${MODEL%.pt}_detection_${STAMP}.json"
REPORT_FILE="${ROOT_DIR}/docs/reports/yolo_detection_smoke.md"
TEGRSTATS_REL="artifacts/system/tegrastats_yolo_${MODEL%.pt}_${STAMP}.log"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
PID=""

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/system"

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
  printf 'tegrastats unavailable; YOLO smoke will run without thermal/power side log\n' >&2
  TEGRASTATS_LOG=""
fi

python3 "${ROOT_DIR}/benchmarks/inference/yolo_detection_smoke.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --model-name "${MODEL}" \
  --device "${DEVICE}" \
  --tegrastats-log "${TEGRSTATS_REL}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

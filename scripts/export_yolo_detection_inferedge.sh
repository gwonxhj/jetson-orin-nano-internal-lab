#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

YOLO_SMOKE="${1:-}"
if [ -z "${YOLO_SMOKE}" ]; then
  YOLO_SMOKE="$(find results/inference -maxdepth 1 -name 'yolo_*_detection_*.json' | sort | tail -n 1)"
fi

if [ -z "${YOLO_SMOKE}" ]; then
  printf 'No YOLO detection smoke JSON found under results/inference\n' >&2
  exit 1
fi

STAMP="$(basename "${YOLO_SMOKE}")"
STAMP="${STAMP#yolo_}"
STAMP="${STAMP#yolov8n_detection_}"
STAMP="${STAMP%.json}"
OUTPUT_DIR="results/inferedge/yolo_yolov8n_detection_${STAMP}"
REPORT_PATH="docs/reports/yolo_inferedge_export.md"

python3 scripts/export_yolo_detection_inferedge.py \
  --yolo-smoke "${YOLO_SMOKE}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

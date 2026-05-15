#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

SOAK_BURST_RESULT="${1:-}"
if [ -z "${SOAK_BURST_RESULT}" ]; then
  SOAK_BURST_RESULT="$(find results/inference -maxdepth 1 -name 'fastapi_resnet18_soak_burst_*.json' | sort | tail -n 1)"
fi

if [ -z "${SOAK_BURST_RESULT}" ]; then
  printf 'No FastAPI ResNet18 soak/burst JSON found under results/inference\n' >&2
  exit 1
fi

STAMP="$(basename "${SOAK_BURST_RESULT}")"
STAMP="${STAMP#fastapi_resnet18_soak_burst_}"
STAMP="${STAMP%.json}"
OUTPUT_DIR="results/inferedge/fastapi_resnet18_soak_burst_${STAMP}"
REPORT_PATH="docs/reports/fastapi_soak_burst_inferedge_export.md"

python3 scripts/export_fastapi_soak_burst_inferedge.py \
  --soak-burst "${SOAK_BURST_RESULT}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

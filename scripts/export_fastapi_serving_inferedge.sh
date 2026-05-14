#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

FASTAPI_SMOKE="${1:-}"
if [ -z "${FASTAPI_SMOKE}" ]; then
  FASTAPI_SMOKE="$(find results/inference -maxdepth 1 -name 'fastapi_resnet18_server_*.json' | sort | tail -n 1)"
fi

if [ -z "${FASTAPI_SMOKE}" ]; then
  printf 'No FastAPI ResNet18 server smoke JSON found under results/inference\n' >&2
  exit 1
fi

STAMP="$(basename "${FASTAPI_SMOKE}")"
STAMP="${STAMP#fastapi_resnet18_server_}"
STAMP="${STAMP%.json}"
OUTPUT_DIR="results/inferedge/resnet18_fastapi_serving_${STAMP}"
REPORT_PATH="docs/reports/fastapi_inferedge_export.md"

python3 scripts/export_fastapi_serving_inferedge.py \
  --fastapi-smoke "${FASTAPI_SMOKE}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

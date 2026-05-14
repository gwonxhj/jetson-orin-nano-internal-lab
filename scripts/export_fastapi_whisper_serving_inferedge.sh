#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

FASTAPI_WHISPER_SMOKE="${1:-}"
if [ -z "${FASTAPI_WHISPER_SMOKE}" ]; then
  FASTAPI_WHISPER_SMOKE="$(find results/inference -maxdepth 1 -name 'fastapi_whisper_speech_server_*.json' | sort | tail -n 1)"
fi

if [ -z "${FASTAPI_WHISPER_SMOKE}" ]; then
  printf 'No FastAPI Whisper speech server smoke JSON found under results/inference\n' >&2
  exit 1
fi

STAMP="$(basename "${FASTAPI_WHISPER_SMOKE}")"
STAMP="${STAMP#fastapi_whisper_speech_server_}"
STAMP="${STAMP%.json}"
OUTPUT_DIR="results/inferedge/fastapi_whisper_serving_${STAMP}"
REPORT_PATH="docs/reports/fastapi_whisper_inferedge_export.md"

python3 scripts/export_fastapi_whisper_serving_inferedge.py \
  --fastapi-whisper-smoke "${FASTAPI_WHISPER_SMOKE}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

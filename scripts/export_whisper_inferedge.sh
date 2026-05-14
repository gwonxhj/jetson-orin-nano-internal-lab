#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_SMOKE="${1:-results/inference/whisper_tiny_speech_transcription_20260514_182822.json}"
RUN_ID="$(basename "${WHISPER_SMOKE}" .json)"
OUTPUT_DIR="${ROOT_DIR}/results/inferedge/${RUN_ID}"
REPORT_PATH="${ROOT_DIR}/docs/reports/whisper_inferedge_export.md"

cd "${ROOT_DIR}"

python3 "${ROOT_DIR}/scripts/export_whisper_inferedge.py" \
  --whisper-smoke "${WHISPER_SMOKE}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

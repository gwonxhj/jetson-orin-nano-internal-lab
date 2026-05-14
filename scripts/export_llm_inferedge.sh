#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LLM_SMOKE="${1:-results/llm/llm_tiny-gpt2_text_generation_20260515_005755.json}"
RUN_ID="$(basename "${LLM_SMOKE}" .json)"
OUTPUT_DIR="${ROOT_DIR}/results/inferedge/${RUN_ID}"
REPORT_PATH="${ROOT_DIR}/docs/reports/llm_inferedge_export.md"

cd "${ROOT_DIR}"

python3 "${ROOT_DIR}/scripts/export_llm_inferedge.py" \
  --llm-smoke "${LLM_SMOKE}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

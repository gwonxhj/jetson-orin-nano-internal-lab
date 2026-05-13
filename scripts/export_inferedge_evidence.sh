#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="${ROOT_DIR}/results/inferedge/resnet18_runtime_compare_${STAMP}"
REPORT="${ROOT_DIR}/docs/reports/inferedge_export.md"

cd "${ROOT_DIR}"
python3 scripts/export_inferedge_evidence.py \
  --output-dir "${OUT_DIR}" \
  --report "${REPORT}"
printf 'Wrote InferEdge-compatible evidence directory: %s\n' "${OUT_DIR}"
printf 'Wrote report: %s\n' "${REPORT}"

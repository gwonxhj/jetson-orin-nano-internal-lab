#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

MULTI_WORKLOAD_RESULT="${1:-}"
if [ -z "${MULTI_WORKLOAD_RESULT}" ]; then
  MULTI_WORKLOAD_RESULT="$(find results/runtime_compare -maxdepth 1 -name 'multi_workload_sustained_*.json' | sort | tail -n 1)"
fi

if [ -z "${MULTI_WORKLOAD_RESULT}" ]; then
  printf 'No multi-workload sustained JSON found under results/runtime_compare\n' >&2
  exit 1
fi

STAMP="$(basename "${MULTI_WORKLOAD_RESULT}")"
STAMP="${STAMP#multi_workload_sustained_}"
STAMP="${STAMP%.json}"
OUTPUT_DIR="results/inferedge/multi_workload_sustained_${STAMP}"
REPORT_PATH="docs/reports/multi_workload_sustained_inferedge_export.md"

python3 scripts/export_multi_workload_sustained_inferedge.py \
  --multi-workload "${MULTI_WORKLOAD_RESULT}" \
  --output-dir "${OUTPUT_DIR}" \
  --report "${REPORT_PATH}"

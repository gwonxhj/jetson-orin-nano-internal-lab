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
OUTPUT_PATH="results/runtime_compare/multi_workload_timeline_${STAMP}.json"
REPORT_PATH="docs/reports/multi_workload_runtime_timeline.md"

python3 benchmarks/runtime_compare/multi_workload_timeline_export.py \
  --multi-workload "${MULTI_WORKLOAD_RESULT}" \
  --output "${OUTPUT_PATH}" \
  --report "${REPORT_PATH}" \
  --bucket-sec "${MULTI_WORKLOAD_TIMELINE_BUCKET_SEC:-10}"

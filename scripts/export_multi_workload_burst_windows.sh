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
TIMELINE_PATH="${MULTI_WORKLOAD_TIMELINE_PATH:-results/runtime_compare/multi_workload_timeline_${STAMP}.json}"
OUTPUT_PATH="results/runtime_compare/multi_workload_burst_windows_${STAMP}.json"
REPORT_PATH="docs/reports/multi_workload_burst_window_report.md"

if [ ! -f "${TIMELINE_PATH}" ]; then
  printf 'Timeline JSON not found: %s\n' "${TIMELINE_PATH}" >&2
  printf 'Run scripts/export_multi_workload_timeline.sh first.\n' >&2
  exit 1
fi

python3 benchmarks/runtime_compare/multi_workload_burst_window_report.py \
  --multi-workload "${MULTI_WORKLOAD_RESULT}" \
  --timeline "${TIMELINE_PATH}" \
  --output "${OUTPUT_PATH}" \
  --report "${REPORT_PATH}" \
  --before-sec "${MULTI_WORKLOAD_BURST_BEFORE_SEC:-60}" \
  --after-sec "${MULTI_WORKLOAD_BURST_AFTER_SEC:-60}"

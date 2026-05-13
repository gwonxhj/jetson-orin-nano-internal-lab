#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/system"
OUT_FILE="${OUT_DIR}/tegrastats_idle.log"
DURATION_SECONDS="${1:-30}"
INTERVAL_MS="${2:-1000}"

mkdir -p "${OUT_DIR}"

if ! command -v tegrastats >/dev/null 2>&1; then
  printf 'tegrastats is unavailable on this system
' >&2
  exit 127
fi

if command -v timeout >/dev/null 2>&1; then
  timeout "${DURATION_SECONDS}s" tegrastats --interval "${INTERVAL_MS}" | tee "${OUT_FILE}"
elif command -v gtimeout >/dev/null 2>&1; then
  gtimeout "${DURATION_SECONDS}s" tegrastats --interval "${INTERVAL_MS}" | tee "${OUT_FILE}"
else
  printf 'timeout command is unavailable; install coreutils or stop tegrastats manually
' >&2
  exit 127
fi

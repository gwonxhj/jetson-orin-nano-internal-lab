#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/artifacts/system"
DURATION_SECONDS="${1:-30}"
INTERVAL_MS="${2:-1000}"
OUT_FILE="${3:-${OUT_DIR}/tegrastats_idle.log}"

mkdir -p "$(dirname "${OUT_FILE}")"

if ! command -v tegrastats >/dev/null 2>&1; then
  printf 'tegrastats is unavailable on this system
' >&2
  exit 127
fi

run_with_timeout() {
  local timeout_cmd="$1"
  set +e
  "${timeout_cmd}" "${DURATION_SECONDS}s" tegrastats --interval "${INTERVAL_MS}" | tee "${OUT_FILE}"
  local status="${PIPESTATUS[0]}"
  set -e

  # GNU timeout returns 124 when it stops the process after the requested duration.
  if [[ "${status}" -eq 124 ]]; then
    return 0
  fi
  return "${status}"
}

if command -v timeout >/dev/null 2>&1; then
  run_with_timeout timeout
elif command -v gtimeout >/dev/null 2>&1; then
  run_with_timeout gtimeout
else
  printf 'timeout command is unavailable; install coreutils or stop tegrastats manually
' >&2
  exit 127
fi

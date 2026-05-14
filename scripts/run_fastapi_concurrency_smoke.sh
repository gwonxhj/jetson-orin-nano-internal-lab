#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
HOST="${FASTAPI_HOST:-127.0.0.1}"
PORT="${FASTAPI_PORT:-18082}"
BASE_URL="http://${HOST}:${PORT}"
RESULT_REL="results/inference/fastapi_resnet18_concurrency_${STAMP}.json"
REPORT_REL="docs/reports/fastapi_concurrency_smoke.md"
SERVER_LOG_REL="artifacts/system/fastapi_concurrency_server_${STAMP}.log"
TEGRSTATS_REL="artifacts/system/tegrastats_fastapi_concurrency_${STAMP}.log"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"
SERVER_LOG="${ROOT_DIR}/${SERVER_LOG_REL}"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
SERVER_PID=""
TEGRASTATS_PID=""

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/system"

cleanup() {
  if [ -n "${SERVER_PID}" ] && kill -0 "${SERVER_PID}" >/dev/null 2>&1; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
  if [ -n "${TEGRASTATS_PID}" ] && kill -0 "${TEGRASTATS_PID}" >/dev/null 2>&1; then
    kill "${TEGRASTATS_PID}" >/dev/null 2>&1 || true
    wait "${TEGRASTATS_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

cd "${ROOT_DIR}"

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "${TEGRSTATS_LOG}" 2>&1 &
  TEGRASTATS_PID="$!"
else
  printf 'tegrastats unavailable; FastAPI concurrency smoke will run without thermal/power side log\n' >&2
  TEGRSTATS_REL=""
fi

JETSON_LAB_SERVER_DEVICE="${JETSON_LAB_SERVER_DEVICE:-cuda}" \
python3 -m uvicorn src.server.resnet18_app:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --log-level info > "${SERVER_LOG}" 2>&1 &
SERVER_PID="$!"

python3 "${ROOT_DIR}/benchmarks/inference/fastapi_concurrency_smoke.py" \
  --base-url "${BASE_URL}" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --server-log "${SERVER_LOG_REL}" \
  --tegrastats-log "${TEGRSTATS_REL}" \
  --levels "${FASTAPI_CONCURRENCY_LEVELS:-1,2,4}" \
  --requests-per-level "${FASTAPI_REQUESTS_PER_LEVEL:-8}" \
  --warmup "${FASTAPI_CONCURRENCY_WARMUP:-2}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
printf 'Wrote server log: %s\n' "${SERVER_LOG}"
if [ -n "${TEGRSTATS_REL}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

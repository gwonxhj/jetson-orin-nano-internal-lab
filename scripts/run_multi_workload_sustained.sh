#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
HOST="${FASTAPI_HOST:-127.0.0.1}"
PORT="${FASTAPI_PORT:-18085}"
BASE_URL="http://${HOST}:${PORT}"
RESULT_REL="results/runtime_compare/multi_workload_sustained_${STAMP}.json"
REPORT_REL="docs/reports/multi_workload_sustained_runtime.md"
SERVER_LOG_REL="artifacts/system/fastapi_multi_workload_server_${STAMP}.log"
TEGRSTATS_REL="artifacts/system/tegrastats_multi_workload_${STAMP}.log"
RESULT_FILE="${ROOT_DIR}/${RESULT_REL}"
REPORT_FILE="${ROOT_DIR}/${REPORT_REL}"
SERVER_LOG="${ROOT_DIR}/${SERVER_LOG_REL}"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
SERVER_PID=""
TEGRASTATS_PID=""

mkdir -p "${ROOT_DIR}/results/runtime_compare" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/system"

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

python3 - <<'PYCHECK'
import importlib.util
import sys
required = ["fastapi", "requests", "torch", "torchvision", "ultralytics", "uvicorn", "whisper"]
missing = [name for name in required if importlib.util.find_spec(name) is None]
if missing:
    print(
        "missing packages for multi-workload sustained run: " + ", ".join(missing) + ". "
        "Activate an env that has both YOLO and Whisper dependencies, for example whisper_env.",
        file=sys.stderr,
    )
    raise SystemExit(2)
PYCHECK

if [ ! -f "examples/audio/license_clear_whisper_smoke.wav" ]; then
  bash scripts/generate_whisper_speech_sample.sh
fi

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval "${MULTI_WORKLOAD_TEGRASTATS_INTERVAL_MS:-1000}" > "${TEGRSTATS_LOG}" 2>&1 &
  TEGRASTATS_PID="$!"
else
  printf 'tegrastats unavailable; multi-workload scenario will run without thermal/power side log\n' >&2
  TEGRSTATS_REL=""
fi

JETSON_LAB_SERVER_DEVICE="${JETSON_LAB_SERVER_DEVICE:-cuda}" \
JETSON_LAB_WHISPER_MODEL="${JETSON_LAB_WHISPER_MODEL:-tiny}" \
python3 -m uvicorn src.server.resnet18_app:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --log-level info > "${SERVER_LOG}" 2>&1 &
SERVER_PID="$!"

python3 "${ROOT_DIR}/benchmarks/runtime_compare/multi_workload_sustained.py" \
  --base-url "${BASE_URL}" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --server-log "${SERVER_LOG_REL}" \
  --tegrastats-log "${TEGRSTATS_REL}" \
  --duration-sec "${MULTI_WORKLOAD_DURATION_SEC:-180}" \
  --fastapi-concurrency "${MULTI_WORKLOAD_FASTAPI_CONCURRENCY:-2}" \
  --fastapi-interval-sec "${MULTI_WORKLOAD_FASTAPI_INTERVAL_SEC:-0.05}" \
  --whisper-start-sec "${MULTI_WORKLOAD_WHISPER_START_SEC:-30}" \
  --whisper-repeat "${MULTI_WORKLOAD_WHISPER_REPEAT:-2}" \
  --whisper-interval-sec "${MULTI_WORKLOAD_WHISPER_INTERVAL_SEC:-2}" \
  --yolo-model "${MULTI_WORKLOAD_YOLO_MODEL:-yolov8n.pt}" \
  --yolo-device "${MULTI_WORKLOAD_YOLO_DEVICE:-auto}" \
  --yolo-interval-sec "${MULTI_WORKLOAD_YOLO_INTERVAL_SEC:-1}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
printf 'Wrote server log: %s\n' "${SERVER_LOG}"
if [ -n "${TEGRSTATS_REL}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi

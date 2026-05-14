#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
MODEL="${1:-tiny}"
RESULT_FILE="${ROOT_DIR}/results/inference/whisper_${MODEL}_transcription_${STAMP}.json"
REPORT_FILE="${ROOT_DIR}/docs/reports/whisper_transcription_smoke.md"
AUDIO_REL="artifacts/audio/whisper_smoke_16khz.wav"
TEGRSTATS_REL="artifacts/system/tegrastats_whisper_${MODEL}_${STAMP}.log"
AUDIO_FILE="${ROOT_DIR}/${AUDIO_REL}"
TEGRSTATS_LOG="${ROOT_DIR}/${TEGRSTATS_REL}"
PID=""
ALLOW_DOWNLOAD_ARGS=()

if [ "${WHISPER_ALLOW_DOWNLOAD:-0}" = "1" ]; then
  ALLOW_DOWNLOAD_ARGS=(--allow-download)
fi

mkdir -p "${ROOT_DIR}/results/inference" "${ROOT_DIR}/docs/reports" "${ROOT_DIR}/artifacts/audio" "${ROOT_DIR}/artifacts/system"

cleanup() {
  if [ -n "${PID}" ] && kill -0 "${PID}" >/dev/null 2>&1; then
    kill "${PID}" >/dev/null 2>&1 || true
    wait "${PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if command -v tegrastats >/dev/null 2>&1; then
  tegrastats --interval 1000 > "${TEGRSTATS_LOG}" 2>&1 &
  PID="$!"
  sleep 1
else
  printf 'tegrastats unavailable; Whisper smoke will run without thermal/power side log\n' >&2
  TEGRASTATS_LOG=""
  TEGRASTATS_REL=""
fi

cd "${ROOT_DIR}"

python3 "${ROOT_DIR}/benchmarks/inference/whisper_transcription_smoke.py" \
  --output "${RESULT_FILE}" \
  --report "${REPORT_FILE}" \
  --audio "${AUDIO_REL}" \
  --model "${MODEL}" \
  --device auto \
  --warmup 0 \
  --repeat 1 \
  --language en \
  --tegrastats-log "${TEGRSTATS_REL}" \
  "${ALLOW_DOWNLOAD_ARGS[@]}"

printf 'Wrote result: %s\n' "${RESULT_FILE}"
printf 'Wrote report: %s\n' "${REPORT_FILE}"
printf 'Wrote audio: %s\n' "${AUDIO_FILE}"
if [ -n "${TEGRSTATS_LOG}" ]; then
  printf 'Wrote tegrastats: %s\n' "${TEGRSTATS_LOG}"
fi
